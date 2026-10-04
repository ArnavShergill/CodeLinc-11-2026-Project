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
test('AI bridge errors fall back to a demo reply when Ollama is unavailable',async()=>{
 const originalFetch=globalThis.fetch;
 globalThis.fetch=async()=>({
  ok:false,
  status:502,
  json:async()=>({error:'Could not reach Ollama at http://127.0.0.1:11434/api/chat. Start Ollama and ensure the model gemma3:latest is available.'})
 });
 try{
  const reply=await askLifeMap('What is life insurance?');
  assert.match(reply,/demo mode|gemma3:latest|sample profile/i);
 }finally{
  globalThis.fetch=originalFetch;
 }
});
test('unavailable Python API falls back to the demo assistant',async()=>{
 const originalFetch=globalThis.fetch;
 globalThis.fetch=async()=>{throw new TypeError('fetch failed');};
 try{
  const reply=await askLifeMap('Hello');
  assert.match(reply,/demo mode|local Ollama service/i);
 }finally{
  globalThis.fetch=originalFetch;
 }
});
test('invalid profile is rejected by adapter',async()=>{await assert.rejects(calculatePlan({...mockProfile,mortgageBalance:-10}),/Mortgage balance/)});
test('hosted demo answers without requesting a visitor local API',async()=>{
 const originalFetch=globalThis.fetch;
 globalThis.window={location:{hostname:'arnavshergill.github.io'}};
 globalThis.fetch=()=>{assert.fail('Hosted demo must not request localhost');};
 try{
  const hosted=await import('../src/services/planService.js?hosted-test');
  assert.match(await hosted.askLifeMap('Hello'),/hosted website/);
  assert.match(await hosted.askLifeMap('My income is $75000'),/hosted website/);
  await assert.rejects(hosted.askLifeMap(' '),/Please add a message/);
 }finally{
  globalThis.fetch=originalFetch;
  delete globalThis.window;
 }
});
test('configured hosted backend returns live chat and surfaces connection failures',async()=>{
 const originalFetch=globalThis.fetch;
 globalThis.window={location:{hostname:'arnavshergill.github.io'},LIFEMAP_CONFIG:{chatApiUrl:'https://api.example.com/api/chat'}};
 globalThis.fetch=async(url)=>{
  assert.equal(url,'https://api.example.com/api/chat');
  return {ok:true,json:async()=>({reply:'Live answer'})};
 };
 try{
  const hosted=await import('../src/services/planService.js?configured-hosted-test');
  assert.equal(await hosted.askLifeMap('Hello'),'Live answer');
  globalThis.fetch=async()=>{throw new TypeError('fetch failed');};
  await assert.rejects(hosted.askLifeMap('Hello'),/Could not reach the LifeMap AI backend/);
  globalThis.fetch=async()=>({ok:false,status:502,json:async()=>({error:'Could not reach Ollama'})});
  await assert.rejects(hosted.askLifeMap('Hello'),/backend is unavailable/);
 }finally{
  globalThis.fetch=originalFetch;
  delete globalThis.window;
 }
});
