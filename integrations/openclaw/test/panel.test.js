import assert from "node:assert/strict";
import test from "node:test";
import { renderSystemPanel } from "../lib/panel.js";
import { collectMachineStatus } from "../lib/status.js";

test("machine status is JSON-compatible and contains no environment values", () => {
  const status = collectMachineStatus();
  assert.equal(status.apiVersion, 1);
  assert.equal(typeof status.hostname, "string");
  assert.equal(typeof status.isClawOS, "boolean");
  assert.equal(typeof status.memory.percent, "number");
  assert.doesNotThrow(() => JSON.stringify(status));
  assert.equal(JSON.stringify(status).includes("process.env"), false);
});

test("panel escapes machine-provided strings", () => {
  const html = renderSystemPanel({
    ...collectMachineStatus(),
    hostname: '<script>alert("x")</script>',
    isClawOS: false,
    broker: {
      available: false,
      message: "clawosd is unavailable; privileged actions are blocked",
    },
  });

  assert.match(html, /&lt;script&gt;alert\(&quot;x&quot;\)&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<script>alert/);
  assert.match(html, /Native recovery stays outside OpenClaw/);
  assert.match(html, /Privileged actions blocked/);
  assert.match(html, /Development host/);
});

test("panel presents the ClawOS-owned update path", () => {
  const status = collectMachineStatus();
  status.openclawVersion = "2026.8.1";
  status.broker = {
    available: true,
    securityLevel: "guarded",
    message: "0 actions waiting for approval",
    openclawUpdate: { targetVersion: "2026.8.2" },
  };
  const html = renderSystemPanel(status, { notice: { message: "Review locally" } });
  assert.match(html, /Review update to 2026\.8\.2/);
  assert.match(html, /method="post"/);
  assert.match(html, /Review locally/);
});

test("panel suppresses a redundant update action", () => {
  const status = collectMachineStatus();
  status.openclawVersion = "2026.8.2";
  status.broker = {
    available: true,
    securityLevel: "full-root",
    message: "0 actions waiting for approval",
    openclawUpdate: { targetVersion: "2026.8.2" },
  };
  const html = renderSystemPanel(status);
  assert.match(html, /OpenClaw 2026\.8\.2 · up to date/);
  assert.doesNotMatch(html, /method="post"/);
});
