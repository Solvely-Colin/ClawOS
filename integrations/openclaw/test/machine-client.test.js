import assert from "node:assert/strict";
import test from "node:test";
import {
  bindMachineToolContext, machineContext, parseNodeMachineRequest, requestMachine, requestRoutedMachine,
} from "../lib/machine-client.js";

test("machine identity uses SDK metadata, not AbortSignal or rewritten model params", async () => {
  const tool = bindMachineToolContext({
    execute(_id, _params, context) { return JSON.parse(machineContext(context)); },
  }, { agentId: "worker", sessionKey: "agent:worker:task" });
  const prepared = tool.prepareBeforeToolCallParams({ agentId: "main", runId: "forged" }, {
    hookContext: { agentId: "worker", sessionKey: "agent:worker:task", runId: "actual-run" },
  });
  const final = tool.finalizeBeforeToolCallParams({ ...prepared, agentId: "main", runId: "other" }, prepared);
  assert.deepEqual(await tool.execute("call", final, new AbortController().signal), {
    agentId: "worker", sessionKey: "agent:worker:task", runId: "actual-run",
  });
  assert.throws(() => tool.prepareBeforeToolCallParams({}, { hookContext: { agentId: "main" } }), /identity changed/);
});

test("separate calls retain their own grant run and direct factory identity", async () => {
  const tool = bindMachineToolContext({ execute(_id, _params, context) { return context; } }, { agentId: "main" });
  const first = tool.prepareBeforeToolCallParams({}, { hookContext: { runId: "one" } });
  const second = tool.prepareBeforeToolCallParams({}, { hookContext: { runId: "two" } });
  assert.equal((await tool.execute("one", first)).runId, "one");
  assert.equal((await tool.execute("two", second)).runId, "two");
  assert.equal((await tool.execute("direct", {})).agentId, "main");
});

test("machine context forwards bounded metadata without claiming authority", () => {
  assert.deepEqual(JSON.parse(machineContext({ agentId: "main", sessionKey: "agent:main:main", runId: "run-1", secret: "no" })), {
    agentId: "main", sessionKey: "agent:main:main", runId: "run-1",
  });
});

test("machine client parses a typed JSON response", async () => {
  const value = await requestMachine(['{"apiVersion":1,"state":"ready"}'], { executable: "/usr/bin/printf" });
  assert.deepEqual(value, { apiVersion: 1, state: "ready" });
});

test("controller routes typed system control to the only compatible ClawOS node", async () => {
  const calls = [];
  const api = { runtime: { nodes: {
    async list() {
      return { nodes: [
        { nodeId: "other", commands: ["system.run"] },
        { nodeId: "claw-1", displayName: "Desk", commands: ["clawos.system"] },
      ] };
    },
    async invoke(request) {
      calls.push(request);
      return { payloadJSON: JSON.stringify({ apiVersion: 1, state: "ready", routed: true }) };
    },
  } } };
  const value = await requestRoutedMachine(api, ["inspect"], {
    localPath: "/definitely/not/clawosctl", forceRemote: true,
  });
  assert.equal(value.routed, true);
  assert.equal(calls[0].nodeId, "claw-1");
  assert.equal(calls[0].command, "clawos.system");
  assert.deepEqual(calls[0].params.args, ["inspect"]);
});

test("node command parser rejects untyped executable input", () => {
  assert.deepEqual(parseNodeMachineRequest('{"args":["status"]}'), ["status"]);
  assert.throws(() => parseNodeMachineRequest('{"args":["/bin/sh","-c","id"]}'), /Unsupported/);
  assert.throws(() => parseNodeMachineRequest('{"args":"status"}'), /bounded/);
});

test("controller refuses ambiguous ClawOS nodes unless one is selected", async () => {
  const api = { runtime: { nodes: {
    async list() {
      return { nodes: [
        { nodeId: "claw-a", displayName: "Desk", commands: ["clawos.system"] },
        { nodeId: "claw-b", displayName: "Rack", commands: ["clawos.system"] },
      ] };
    },
    async invoke(request) { return { payload: { selected: request.nodeId } }; },
  } } };
  await assert.rejects(
    requestRoutedMachine(api, ["status"], { localPath: "/missing", forceRemote: true }),
    /More than one/,
  );
  const selected = await requestRoutedMachine(api, ["status"], {
    localPath: "/missing", forceRemote: true, nodeId: "Rack",
  });
  assert.equal(selected.selected, "claw-b");
});
