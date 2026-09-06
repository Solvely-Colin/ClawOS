import assert from "node:assert/strict";
import test from "node:test";
import {
  CLAWOS_SYSTEM_CONTEXT,
  buildEmbodimentHookResult,
  clawosSystemContext,
  rawGuiLaunchBlock,
  rawPrivilegedBlock,
  resolvePresentationIntent,
} from "../lib/embodiment.js";

const applications = [
  { id: "web:gmail", name: "Gmail", kind: "web", browserProfile: "clawos-gmail" },
  { id: "web:outlook", name: "Outlook", kind: "web" },
  { id: "desktop:chromium", name: "Chromium", kind: "desktop" },
];

test("embodiment establishes a graphical activity-owned machine", () => {
  assert.match(CLAWOS_SYSTEM_CONTEXT, /not a\s+headless server/i);
  assert.match(CLAWOS_SYSTEM_CONTEXT, /use clawos_app/i);
  assert.match(CLAWOS_SYSTEM_CONTEXT, /supporting surfaces attached/i);
});

test("raw privileged commands are blocked but read-only diagnostics remain available", () => {
  const guarded = { fullRoot: false };
  assert.ok(rawPrivilegedBlock({ toolName: "exec", params: { command: "sudo pacman -S tree" } }, guarded));
  assert.ok(rawPrivilegedBlock({ toolName: "exec", params: { command: "echo ready; systemctl restart sshd" } }, guarded));
  assert.ok(rawPrivilegedBlock({ toolName: "exec", params: { command: "/usr/bin/btrfs subvolume delete /x" } }, guarded));
  assert.ok(rawPrivilegedBlock({ toolName: "exec", params: { command: "/usr/lib/clawos/clawosctl commit token" } }, guarded));
  assert.equal(rawPrivilegedBlock({ toolName: "exec", params: { command: "/usr/lib/clawos/clawosctl status" } }, guarded), null);
  assert.equal(rawPrivilegedBlock({ toolName: "exec", params: { command: "cat /proc/version" } }, guarded), null);
  assert.equal(rawPrivilegedBlock({ toolName: "clawos_system", params: { action: "status" } }, guarded), null);
});

test("explicit Full Root mode permits privileged exec", () => {
  assert.equal(rawPrivilegedBlock(
    { toolName: "exec", params: { command: "sudo systemctl restart sshd" } },
    { fullRoot: true },
  ), null);
  assert.ok(rawPrivilegedBlock(
    { toolName: "exec", params: { command: "sudo systemctl restart sshd" } },
    { fullRoot: true, agentId: "reviewer" },
  ));
});

test("Full Root context gives the core agent real machine authority", () => {
  const context = clawosSystemContext({ fullRoot: true });
  assert.match(context, /core system agent/i);
  assert.match(context, /passwordless root authority/i);
  assert.match(context, /never claim you cannot/i);
  assert.match(context, /privileged exec when no typed capability exists/i);
  assert.doesNotMatch(clawosSystemContext({ fullRoot: false, agentId: "reviewer" }), /passwordless root authority/i);
});

test("explicit natural presentation requests resolve through the validated registry", () => {
  assert.equal(resolvePresentationIntent("open gmail", applications), "web:gmail");
  assert.equal(resolvePresentationIntent("Please bring up Outlook", applications), "web:outlook");
  assert.equal(resolvePresentationIntent("Can you open up Gmail?", applications), "web:gmail");
  assert.equal(resolvePresentationIntent("check whether Gmail has new mail", applications), null);
  assert.equal(resolvePresentationIntent("I have an open question about Gmail", applications), null);
  assert.equal(resolvePresentationIntent("open mail", applications), null);
});

test("the per-turn hint names only the resolved validated id", () => {
  const result = buildEmbodimentHookResult("show me Gmail", applications);
  assert.equal(result.appendSystemContext, CLAWOS_SYSTEM_CONTEXT);
  assert.match(result.prependContext, /appId=web:gmail/);
  assert.match(result.prependContext, /profile=clawos-gmail/);
  assert.doesNotMatch(result.prependContext, /xdg-open.*allowed/i);
});

test("raw graphical launch commands are blocked but diagnostics are not", () => {
  assert.ok(rawGuiLaunchBlock({ toolName: "exec", params: { command: "chromium https://mail.google.com" } }));
  assert.ok(rawGuiLaunchBlock({ toolName: "exec", params: { command: "/usr/bin/chromium https://mail.google.com" } }));
  assert.ok(rawGuiLaunchBlock({ toolName: "exec", params: { command: "gio launch /usr/share/applications/example.desktop" } }));
  assert.ok(rawGuiLaunchBlock({ toolName: "exec", params: { command: "echo ready; xdg-open https://example.com" } }));
  assert.equal(rawGuiLaunchBlock({ toolName: "exec", params: { command: "which chromium" } }), null);
  assert.equal(rawGuiLaunchBlock({ toolName: "clawos_app", params: { action: "open" } }), null);
});
