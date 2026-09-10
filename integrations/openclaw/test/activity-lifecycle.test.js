import assert from "node:assert/strict";
import test from "node:test";
import { createActivityLifecycle } from "../lib/activity-lifecycle.js";

function recorder() {
  const requests = [];
  return { requests, request: async (value) => { requests.push(value); return value; } };
}

test("agent lifecycle projects running and completion without conversation content", async () => {
  const recorded = recorder();
  const lifecycle = createActivityLifecycle({ request: recorded.request });

  await lifecycle.modelCallStarted({ runId: "run-1", sessionKey: "agent:main:main" }, { agentId: "main" });
  await lifecycle.agentEnded({ runId: "run-1", success: true, durationMs: 2400 }, { agentId: "main" });

  assert.deepEqual(recorded.requests, [
    { action: "activity.update", state: "running", summary: "Agent main is working" },
    { action: "activity.update", state: "complete", summary: "Agent run complete in 2s" },
  ]);
  assert.deepEqual(lifecycle.status(), { activeRuns: 0, delegatedSessions: 0 });
});

test("concurrent runs remain running until the final run ends", async () => {
  const recorded = recorder();
  const lifecycle = createActivityLifecycle({ request: recorded.request });

  await lifecycle.modelCallStarted({ runId: "run-1" }, { agentId: "main" });
  await lifecycle.modelCallStarted({ runId: "run-2" }, { agentId: "review" });
  await lifecycle.agentEnded({ runId: "run-1", success: true }, { agentId: "main" });

  assert.equal(recorded.requests.at(-1).state, "running");
  assert.deepEqual(lifecycle.status(), { activeRuns: 1, delegatedSessions: 0 });
});

test("failed delegated work raises native attention", async () => {
  const recorded = recorder();
  const lifecycle = createActivityLifecycle({ request: recorded.request });

  await lifecycle.subagentSpawned({ childSessionKey: "agent:worker:one", agentId: "worker", runId: "run-child" });
  await lifecycle.subagentEnded({ targetSessionKey: "agent:worker:one", outcome: "error" });

  assert.deepEqual(recorded.requests.slice(-2), [
    { action: "activity.update", state: "needs-attention", summary: "Delegated work needs attention" },
    { action: "attention.set", kind: "attention", message: "A delegated agent did not complete" },
  ]);
});

test("projection failures never fail the OpenClaw run", async () => {
  const lifecycle = createActivityLifecycle({ request: async () => { throw new Error("socket absent"); } });
  await assert.doesNotReject(() => lifecycle.modelCallStarted({ runId: "run-1" }, { agentId: "main" }));
  await assert.doesNotReject(() => lifecycle.agentEnded({ runId: "run-1", success: false }, { agentId: "main" }));
});
