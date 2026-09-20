import assert from "node:assert/strict";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import test from "node:test";
import { createHash } from 'node:crypto';

const brokerPath = new URL("../profile-overlay/airootfs/usr/lib/clawos/clawos-surfaced", import.meta.url).pathname;

async function waitForSocket(socketPath) {
  const deadline = Date.now() + 3000;
  while (Date.now() < deadline) {
    if (fs.existsSync(socketPath)) return;
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  throw new Error("surface broker socket did not appear");
}

function request(socketPath, payload) {
  return new Promise((resolve, reject) => {
    const socket = net.createConnection(socketPath);
    let output = "";
    socket.setEncoding("utf8");
    socket.on("connect", () => socket.write(`${JSON.stringify(payload)}\n`));
    socket.on("data", (chunk) => { output += chunk; });
    socket.on("error", reject);
    socket.on("close", () => {
      try { resolve(JSON.parse(output).result); } catch (error) { reject(error); }
    });
  });
}

async function stop(child) {
  if (child.exitCode !== null) return;
  child.kill("SIGTERM");
  await new Promise((resolve) => child.once("exit", resolve));
}

test("surface broker restores minimal activity state safely", async (t) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "clawos-surfaced-"));
  const runtime = path.join(temporary, "runtime");
  const persistent = path.join(temporary, "state");
  fs.mkdirSync(runtime, { mode: 0o700 });
  const socketPath = path.join(runtime, "clawos", "surface.sock");
  const env = {
    ...process.env,
    XDG_RUNTIME_DIR: runtime,
    XDG_STATE_HOME: persistent,
    CLAWOS_SURFACE_SOCKET: socketPath,
  };
  const children = [];
  t.after(async () => {
    for (const child of children) await stop(child);
    fs.rmSync(temporary, { recursive: true, force: true });
  });

  const first = spawn(process.execPath, [brokerPath], { env, stdio: "ignore" });
  children.push(first);
  await waitForSocket(socketPath);

  const duplicate = spawn(process.execPath, [brokerPath], { env, stdio: "ignore" });
  children.push(duplicate);
  const duplicateExit = await new Promise((resolve) => duplicate.once("exit", (code) => resolve(code)));
  assert.equal(duplicateExit, 0);
  const stillOwned = await request(socketPath, { action: "status" });
  assert.equal(stillOwned.surface.visible, "agent");

  await request(socketPath, {
    action: "activity.update",
    title: "Persisted activity",
    summary: "Work was running",
    state: "running",
  });
  await stop(first);

  const persistedPath = path.join(persistent, 'clawos/activity.json');
  const saved = JSON.parse(fs.readFileSync(persistedPath, 'utf8'));
  const key = 'agent:main:restored-task';
  const identifier = createHash('sha256').update(key).digest('hex').slice(0, 24);
  saved.tasks = {[identifier]: {sessionKey: key}};
  fs.writeFileSync(persistedPath, JSON.stringify(saved));

  const second = spawn(process.execPath, [brokerPath], { env, stdio: "ignore" });
  children.push(second);
  await waitForSocket(socketPath);
  const restored = await request(socketPath, { action: "status" });

  assert.equal(restored.activity.title, "Persisted activity");
  assert.equal(restored.activity.state, "waiting");
  assert.equal(restored.activity.summary, "Work restored; waiting for Gateway activity");
  assert.equal(restored.surface.visible, "agent");
  assert.deepEqual(restored.tasks, {[identifier]: {sessionKey: key}});
});

test('a replacement compositor takes over a broker with a dead socket', async (t) => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'clawos-compositor-'));
  const runtime = path.join(temporary, 'runtime');
  fs.mkdirSync(runtime);
  const oldSway = path.join(runtime, 'old-sway.sock');
  const newSway = path.join(runtime, 'new-sway.sock');
  fs.writeFileSync(oldSway, 'test compositor');
  fs.writeFileSync(newSway, 'test compositor');
  const socketPath = path.join(runtime, 'clawos', 'surface.sock');
  const env = {...process.env, XDG_RUNTIME_DIR: runtime,
    XDG_STATE_HOME: path.join(temporary, 'state'), CLAWOS_SURFACE_SOCKET: socketPath};
  const children = [];
  t.after(async () => {
    for (const child of children) await stop(child);
    fs.rmSync(temporary, {recursive: true, force: true});
  });
  const first = spawn(process.execPath, [brokerPath], {env: {...env, SWAYSOCK: oldSway}, stdio: 'ignore'});
  children.push(first);
  await waitForSocket(socketPath);
  await request(socketPath, {action: 'activity.update', title: 'Preserve this task'});
  fs.unlinkSync(oldSway);
  const oldExit = new Promise((resolve) => first.once('exit', resolve));
  const second = spawn(process.execPath, [brokerPath], {env: {...env, SWAYSOCK: newSway}, stdio: 'ignore'});
  children.push(second);
  await oldExit;
  await waitForSocket(socketPath);
  assert.equal((await request(socketPath, {action: 'status'})).activity.title, 'Preserve this task');
  assert.equal(fs.readFileSync(path.join(runtime, 'clawos/surfaced.lock/pid'), 'utf8').trim(), String(second.pid));
});
