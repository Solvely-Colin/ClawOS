import { requestSurface } from "./surface-client.js";

function agentLabel(context = {}) {
  if (context.agentId) return `Agent ${context.agentId}`;
  const match = typeof context.sessionKey === "string" ? context.sessionKey.match(/^agent:([^:]+)/) : null;
  return match ? `Agent ${match[1]}` : "Agent";
}

function durationSummary(durationMs) {
  if (!Number.isFinite(durationMs) || durationMs < 1000) return "Agent run complete";
  const seconds = Math.max(1, Math.round(durationMs / 1000));
  return `Agent run complete in ${seconds}s`;
}

export function createActivityLifecycle(options = {}) {
  const send = options.request || ((request) => requestSurface(request, { timeoutMs: 1000 }));
  const activeRuns = new Map();
  const delegatedSessions = new Map();

  async function project(request) {
    try {
      return await send(request);
    } catch {
      // Shell projection must never block or fail an OpenClaw run. The broker
      // may legitimately be absent on a remote Gateway or during logout.
      return null;
    }
  }

  function runningSummary() {
    if (delegatedSessions.size > 0) {
      return `${delegatedSessions.size} delegated agent${delegatedSessions.size === 1 ? "" : "s"} working`;
    }
    const latest = [...activeRuns.values()].at(-1);
    return `${latest?.agent || "Agent"} is working`;
  }

  return {
    async modelCallStarted(event = {}, context = {}) {
      const runId = event.runId || context.runId;
      if (runId) activeRuns.set(runId, { agent: agentLabel(context), sessionKey: event.sessionKey || context.sessionKey });
      await project({ action: "activity.update", state: "running", summary: runningSummary() });
    },

    async agentEnded(event = {}, context = {}) {
      const runId = event.runId || context.runId;
      if (runId) activeRuns.delete(runId);
      if (activeRuns.size > 0 || delegatedSessions.size > 0) {
        await project({ action: "activity.update", state: "running", summary: runningSummary() });
        return;
      }
      await project({
        action: "activity.update",
        state: event.success === false ? "failed" : "complete",
        summary: event.success === false ? "Agent run failed" : durationSummary(event.durationMs),
      });
    },

    async subagentSpawned(event = {}) {
      if (event.childSessionKey) {
        delegatedSessions.set(event.childSessionKey, { agentId: event.agentId, label: event.label, runId: event.runId });
      }
      await project({ action: "activity.update", state: "running", summary: runningSummary() });
    },

    async subagentEnded(event = {}) {
      if (event.targetSessionKey) delegatedSessions.delete(event.targetSessionKey);
      const failed = event.outcome && event.outcome !== "ok";
      if (activeRuns.size > 0 || delegatedSessions.size > 0) {
        await project({ action: "activity.update", state: "running", summary: runningSummary() });
        return;
      }
      await project({
        action: "activity.update",
        state: failed ? "needs-attention" : "complete",
        summary: failed ? "Delegated work needs attention" : "Delegated work complete",
      });
      if (failed) {
        await project({ action: "attention.set", kind: "attention", message: "A delegated agent did not complete" });
      }
    },

    status() {
      return { activeRuns: activeRuns.size, delegatedSessions: delegatedSessions.size };
    },
  };
}
