import test from 'node:test';
import assert from 'node:assert/strict';
import {mockProfile} from '../src/data/mockProfile.js';
import {mockResult} from '../src/data/mockResult.js';
import {validateProfile} from '../src/types/contracts.js';
import {askLifeMap,calculatePlan,sendIntakeMessage} from '../src/services/planService.js';
test('contract fixture is complete and invalid values are rejected',()=>{assert.deepEqual(validateProfile(mockProfile),[]);for(const annualIncome of [undefined,NaN,-1])assert.ok(validateProfile({...mockProfile,annualIncome}).includes('Annual income'));assert.ok(validateProfile({...mockProfile,childrenAges:[NaN]}).length);});
test('profile edits cannot silently alter the mock coverage result',async()=>{const response=await calculatePlan({...mockProfile,annualIncome:123456});assert.equal(response.source,'mock');assert.deepEqual(response.result,mockResult);response.result.breakdown.pop();assert.equal(mockResult.breakdown.length,5);});
test('intake calls the Python AI bridge while keeping profile values synthetic',async()=>{
 const originalFetch=globalThis.fetch;
 let request;
 globalThis.fetch=async(url,options)=>{
  request={url,options};
  return {ok:true,json:async()=>({reply:'Thanks for sharing that.'})};
 };
 try{
  const response=await sendIntakeMessage({
   profile:mockProfile,
   questionIndex:0,
   message:'I earn $9 million',
   conversation:[{role:'customer',text:'I earn $9 million'}]
  });
  assert.equal(request.url,'http://127.0.0.1:8000/api/chat');
  assert.equal(JSON.parse(request.options.body).conversation[0].role,'user');
  assert.equal(response.reply,'Thanks for sharing that.');
  assert.equal(response.profile.annualIncome,75000);
  assert.equal(response.source,'live-ai');
  assert.equal(response.profileSource,'mock');
 }finally{
  globalThis.fetch=originalFetch;
 }
});
test('AI bridge errors are shown to callers',async()=>{
 const originalFetch=globalThis.fetch;
 globalThis.fetch=async()=>({
  ok:false,
  status:502,
  json:async()=>({error:'Start Ollama and check the model.'})
 });
 try{
  await assert.rejects(askLifeMap('What is life insurance?'),/Start Ollama/);
 }finally{
  globalThis.fetch=originalFetch;
 }
});
test('unavailable Python API reports how to start the service',async()=>{
 const originalFetch=globalThis.fetch;
 globalThis.fetch=async()=>{throw new TypeError('fetch failed');};
 try{
  await assert.rejects(askLifeMap('Hello'),/npm run api/);
 }finally{
  globalThis.fetch=originalFetch;
 }
});
test('invalid profile is rejected by adapter',async()=>{await assert.rejects(calculatePlan({...mockProfile,mortgageBalance:-10}),/Mortgage balance/)});
