import { test, expect } from '@playwright/test';
import { readFile, writeFile } from 'node:fs/promises';

for (const [mode, port] of [['development', 5179], ['production', 5180]]) {
  test(`${mode}: renders and opens the conversation without runtime errors`, async ({ page }) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    // Mock external branding/fonts are not part of the dependency contract.
    await page.route(/https:\/\//, route => route.abort());
    await page.goto(`http://127.0.0.1:${port}`);
    await expect(page.getByRole('region', { name: 'Gmail application' })).toBeVisible();
    await page.getByRole('button', { name: 'Agent actions', exact: true }).click();
    await page.getByRole('button', { name: /Open conversation/ }).click();
    await expect(page.getByRole('complementary', { name: 'OpenClaw conversation' })).toBeVisible();
    await page.getByRole('button', { name: 'Close conversation' }).click();
    await expect(page.getByRole('complementary', { name: 'OpenClaw conversation' })).not.toBeVisible();
    expect(errors).toEqual([]);
  });
}

test('development: React Fast Refresh updates JSX and preserves input state', async ({ page }) => {
  const source = new URL('../src/App.jsx', import.meta.url);
  const original = await readFile(source, 'utf8');
  const before = 'Gateway online';
  const after = 'Gateway HMR smoke';
  expect(original).toContain(before);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route(/https:\/\//, route => route.abort());
  await page.goto('http://127.0.0.1:5179');
  const input = page.getByPlaceholder('Ask Agent about Gmail…');
  await input.fill('preserve this draft');
  try {
    await writeFile(source, original.replace(before, after));
    await expect(page.getByText(after, { exact: true })).toBeVisible();
    await expect(input).toHaveValue('preserve this draft');
    expect(errors).toEqual([]);
  } finally {
    await writeFile(source, original);
  }
  await expect(page.getByText(before, { exact: true })).toBeVisible();
});
