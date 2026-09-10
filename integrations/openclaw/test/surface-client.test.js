import assert from "node:assert/strict";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { requestSurface, toolResult } from "../lib/surface-client.js";

test("surface client sends one typed newline-delimited request", async (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "clawos-surface-"));
  const socketPath = path.join(directory, "surface.sock");
  const server = net.createServer((connection) => {
    connection.setEncoding("utf8");
    connection.once("data", (data) => {
      assert.deepEqual(JSON.parse(data.trim()), { action: "surface.present", surface: "browser" });
      connection.end(`${JSON.stringify({ ok: true, result: { surface: { visible: "browser" } } })}\n`);
    });
  });
  await new Promise((resolve) => server.listen(socketPath, resolve));
  t.after(() => { server.close(); fs.rmSync(directory, { recursive: true, force: true }); });

  const result = await requestSurface({ action: "surface.present", surface: "browser" }, { socketPath });
  assert.equal(result.surface.visible, "browser");
});

test("tool result is valid OpenClaw text content", () => {
  const result = toolResult({ ok: true });
  assert.deepEqual(result.content, [{ type: "text", text: '{"ok":true}' }]);
  assert.deepEqual(result.details, { ok: true });
});
