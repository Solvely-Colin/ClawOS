import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const terminal = new Set(['complete', 'rolled-back', 'failed', 'recovery-required']);
export function targetHash(target) {
  return createHash('sha256').update(`${target.sessionKey}\n${target.sessionId}`).digest('hex');
}
export function notice(r) {
  return `ClawOS runtime update: ${r.state}.\nJob: ${r.jobId}\nVersion: ${r.version}\nHealth verified: ${r.healthVerified ? 'yes' : 'no'}\nRecovery checkpoint: ${r.snapshot || 'not created'}\n${r.recoveryScope}`;
}
// Version-pinned adapter: upstream owns transactional deduplication and storage.
async function adapter() {
  const root = '/usr/lib/node_modules/openclaw';
  const pkg = JSON.parse(await readFile(`${root}/package.json`, 'utf8'));
  if (pkg.version !== '2026.8.2') throw new Error('Unsupported delivery adapter version');
  const store = await import(`${root}/dist/session-utils-store-DTIW0l2Y.js`);
  const transcript = await import(`${root}/dist/chat-transcript-persistence-9fL5y0to.js`);
  return {load: store.i, append: transcript.t};
}
export async function deliver(params, dependencies = {}) {
  if (!/^[0-9a-f-]{36}$/.test(params.jobId || '')) throw new Error('Invalid deployment ID');
  const r = await (dependencies.receipt || (async id => JSON.parse(await readFile(`/var/lib/clawos/deploy-receipts/${id}.json`, 'utf8'))))(params.jobId);
  if (!terminal.has(r.state) || r.targetHash !== targetHash(params)) throw new Error('Receipt is not terminal or destination does not match');
  const runtime = dependencies.runtime || await adapter();
  const target = runtime.load(params.sessionKey);
  if (target.canonicalKey !== params.sessionKey || target.entry?.sessionId !== params.sessionId || target.entry?.archivedAt != null) throw new Error('Original conversation unavailable');
  const result = await runtime.append({sessionKey: params.sessionKey, sessionId: params.sessionId,
    expectedSessionId: params.sessionId, storePath: target.storePath, cfg: target.cfg,
    createIfMissing: false, message: notice(r), label: 'ClawOS update',
    idempotencyKey: `clawos-deploy:${params.jobId}:${r.state}`});
  if (!result.ok || !result.messageId) throw new Error('Append was not acknowledged');
  return result;
}
export function registerDeploymentDelivery(api) {
  api.registerGatewayMethod('clawos.deploy.resolve', async ({params, respond}) => {
    try {
      if (typeof params.sessionKey !== 'string' || !/^agent:[a-zA-Z0-9_-]+:.{1,200}$/.test(params.sessionKey)) throw new Error('Invalid session key');
      const target = (await adapter()).load(params.sessionKey);
      if (!target.entry?.sessionId || target.entry.archivedAt != null) throw new Error('Conversation unavailable');
      respond(true, {sessionKey: target.canonicalKey, sessionId: target.entry.sessionId});
    } catch { respond(false, undefined, {code: 'UNAVAILABLE', message: 'Cannot bind deployment conversation'}); }
  }, {scope: 'operator.admin'});
  api.registerGatewayMethod('clawos.deploy.deliver', async ({params, respond, context}) => {
    try {
      const result = await deliver(params);
      context.broadcast('chat', {runId: `inject-${result.messageId}`, sessionKey: params.sessionKey,
        seq: 0, state: 'final', message: result.message}, {sessionKeys: [params.sessionKey]});
      respond(true, {messageId: result.messageId});
    } catch { respond(false, undefined, {code: 'UNAVAILABLE', message: 'Delivery awaits a compatible Gateway and original conversation'}); }
  }, {scope: 'operator.admin'});
}
