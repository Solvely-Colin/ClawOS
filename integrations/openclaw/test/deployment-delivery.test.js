import test from 'node:test';
import assert from 'node:assert/strict';
import {deliver, targetHash, notice} from '../lib/deployment-delivery.js';
const params = {jobId:'11111111-1111-4111-8111-111111111111',sessionKey:'agent:main:test',sessionId:'original'};
function fixture(state='complete') {
  const receipt={...params,state,version:'v1',targetHash:targetHash(params),healthVerified:true,recoveryScope:'Runtime files only'};
  let calls=0;
  const runtime={load:()=>({canonicalKey:params.sessionKey,entry:{sessionId:'original'},storePath:'store'}),
    append:async options=>{calls++;assert.equal(options.expectedSessionId,'original');assert.equal(options.createIfMissing,false);return {ok:true,messageId:options.idempotencyKey,message:{role:'assistant'}};}};
  return {receipt:async()=>receipt,runtime,count:()=>calls};
}
test('completion, rollback and failure have deterministic outcome identities',async()=>{
  for(const state of ['complete','rolled-back','failed','recovery-required']){
    const f=fixture(state);const first=await deliver(params,f);const retry=await deliver(params,f);
    assert.equal(first.messageId,retry.messageId);assert.match(first.messageId,new RegExp(state));
  }
});
test('pending, wrong conversation and replaced session fail without appending',async()=>{
  await assert.rejects(deliver(params,fixture('applying')));
  await assert.rejects(deliver({...params,sessionKey:'agent:main:other'},fixture()));
  const f=fixture();f.runtime.load=()=>({canonicalKey:params.sessionKey,entry:{sessionId:'replacement'}});
  await assert.rejects(deliver(params,f));assert.equal(f.count(),0);
});
test('receipt notice does not include raw errors',()=>{
  assert.ok(!notice({state:'failed',jobId:params.jobId,error:'private credential'}).includes('private credential'));
});
