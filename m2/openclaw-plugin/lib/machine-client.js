import { execFile } from "node:child_process";
import { access } from "node:fs/promises";

const CTL = "/usr/lib/clawos/clawosctl";

export function requestMachine(args, options = {}) {
  const executable = options.executable || CTL;
  const timeout = options.timeoutMs || 10_000;
  return new Promise((resolve, reject) => {
    execFile(executable, args, { timeout, maxBuffer: 256 * 1024 }, (error, stdout, stderr) => {
      if (error) return reject(new Error(String(stderr || error.message).trim()));
      try {
        resolve(JSON.parse(stdout));
      } catch (parseError) {
        reject(new Error(`Invalid ClawOS broker response: ${parseError.message}`));
      }
    });
  });
}

export function machineContext(context = {}) {
  return JSON.stringify({
    agentId: typeof context.agentId === "string" ? context.agentId : "",
    sessionKey: typeof context.sessionKey === "string" ? context.sessionKey : "",
    runId: typeof context.runId === "string" ? context.runId : "",
  });
}

// OpenClaw 2026.8.2 execute receives AbortSignal, NOT agent context. Bind the
// factory identity and per-call hook run ID outside model-controlled params.
// WeakMap retains no completed-call registry and survives hook param rewrites
// through the SDK's tool-owned preparation/finalization contract.
export function bindMachineToolContext(tool, factoryContext = {}) {
  const contexts = new WeakMap();
  return {
    ...tool,
    prepareBeforeToolCallParams(params, { hookContext = {} } = {}) {
      for (const key of ["agentId", "sessionKey"]) {
        if (factoryContext[key] && hookContext[key] && factoryContext[key] !== hookContext[key]) {
          throw new Error("Machine tool runtime identity changed.");
        }
      }
      const prepared = { ...params };
      contexts.set(prepared, {
        agentId: factoryContext.agentId || hookContext.agentId,
        sessionKey: factoryContext.sessionKey || hookContext.sessionKey,
        runId: hookContext.runId,
      });
      return prepared;
    },
    finalizeBeforeToolCallParams(params, prepared) {
      const final = { ...params };
      contexts.set(final, contexts.get(prepared) || factoryContext);
      return final;
    },
    execute(callId, params) {
      return tool.execute(callId, params, contexts.get(params) || factoryContext);
    },
  };
}

function nodePayload(result) {
  if (result && typeof result.payload === "object" && result.payload !== null) return result.payload;
  if (typeof result?.payloadJSON === "string") return JSON.parse(result.payloadJSON);
  throw new Error("The selected ClawOS node returned an invalid system response.");
}

export async function requestRoutedMachine(api, args, options = {}) {
  const localPath = options.localPath || CTL;
  const forceRemote = options.forceRemote === true;
  if (!forceRemote) {
    try {
      await access(localPath);
      return await requestMachine(args, { ...options, executable: localPath });
    } catch (error) {
      if (error?.code !== "ENOENT" && error?.code !== "EACCES") throw error;
    }
  }

  const listed = await api.runtime.nodes.list({ connected: true });
  const candidates = (Array.isArray(listed?.nodes) ? listed.nodes : []).filter(
    (node) => Array.isArray(node.commands) && node.commands.includes("clawos.system"),
  );
  const requested = typeof options.nodeId === "string" ? options.nodeId.trim() : "";
  const matches = requested
    ? candidates.filter((node) => node.nodeId === requested || node.displayName === requested)
    : candidates;
  if (matches.length === 0) {
    throw new Error(requested
      ? `ClawOS node ${JSON.stringify(requested)} is not connected with system control.`
      : "No paired ClawOS node is connected with system control.");
  }
  if (matches.length > 1) throw new Error("More than one ClawOS node is connected; specify targetNode.");
  return nodePayload(await api.runtime.nodes.invoke({
    nodeId: matches[0].nodeId,
    command: "clawos.system",
    params: { args },
    timeoutMs: options.timeoutMs || 10_000,
  }));
}

export function parseNodeMachineRequest(paramsJSON) {
  let payload;
  try {
    payload = JSON.parse(paramsJSON || "{}");
  } catch {
    throw new Error("Invalid ClawOS node request.");
  }
  if (!Array.isArray(payload.args) || payload.args.length < 1 || payload.args.length > 6) {
    throw new Error("A bounded ClawOS command argument list is required.");
  }
  if (payload.args.some((value) => typeof value !== "string" || value.length > 4096)) {
    throw new Error("Invalid ClawOS command argument.");
  }
  const allowed = new Set(["status", "inspect", "capabilities", "action", "pending", "prepare", "cancel", "commit"]);
  if (!allowed.has(payload.args[0])) throw new Error("Unsupported ClawOS node operation.");
  return payload.args;
}
