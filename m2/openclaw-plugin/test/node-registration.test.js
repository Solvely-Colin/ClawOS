import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("plugin source registers a typed dangerous node command and matching policy", async () => {
  const source = await readFile(new URL("../index.js", import.meta.url), "utf8");
  assert.match(source, /registerNodeHostCommand\(\{[\s\S]*?command: "clawos\.system"[\s\S]*?dangerous: true/);
  assert.match(source, /registerNodeInvokePolicy\(\{[\s\S]*?commands: \["clawos\.system"\][\s\S]*?dangerous: true/);
  assert.match(source, /requestRoutedMachine/);
});
