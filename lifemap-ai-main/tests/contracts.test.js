import test from 'node:test';
import assert from 'node:assert/strict';
import {mockProfile} from '../src/data/mockProfile.js';
import {mockResult} from '../src/data/mockResult.js';
import {validateProfile} from '../src/types/contracts.js';
import {askLifeMap,calculatePlan,sendIntakeMessage,emptyProfile,nextQuestionIndex,validateResult} from '../src/services/planService.js';
async function withFetch(fake,work){const original=globalThis.fetch;globalThis.fetch=fake;try{return await work();}finally{globalThis.fetch=original;}}
test('new profiles contain no invented customer facts and missing details stay missing',()=>{
 const profile=emptyProfile();assert.ok(Object.values(profile).every(value=>value===null));assert.equal(nextQuestionIndex(profile),0);
 assert.equal(nextQuestionIndex({...profile,annualIncome:90000}),1);assert.equal(nextQuestionIndex(mockProfile),-1);
 assert.ok(validateProfile({...mockProfile,childrenAges:[NaN]}).length);
});
test('intake sends confirmed context and returns proposed facts without mutating the profile',async()=>{
 const profile=emptyProfile();
 await withFetch(async(url,options)=>{
  assert.equal(url,'http://127.0.0.1:8000/api/intake');const body=JSON.parse(options.body);
  assert.equal(body.field,'annualIncome');assert.equal(body.consent,true);assert.deepEqual(body.context.profile,profile);
  return {ok:true,json:async()=>({reply:'Please confirm.',updates:{annualIncome:90000,numberOfDependents:2}})};
 },async()=>{const response=await sendIntakeMessage({profile,questionIndex:0,message:'I earn 90k and have two dependents',consent:true});assert.deepEqual(response.updates,{annualIncome:90000,numberOfDependents:2});assert.equal(profile.annualIncome,null);});
});
test('invalid extracted values are rejected rather than committed',async()=>{
 for(const updates of [{annualIncome:-1},{numberOfDependents:1.5},{inflationRate:2},{childrenAges:[999]}]){
  await withFetch(async()=>({ok:true,json:async()=>({reply:'Confirm',updates})}),async()=>{await assert.rejects(sendIntakeMessage({profile:emptyProfile(),questionIndex:0,message:'hello',consent:true}),/invalid details/);});
 }
});
test('chat sends recent history and confirmed calculator context with explicit consent',async()=>{
 await withFetch(async(url,options)=>{const body=JSON.parse(options.body);assert.equal(body.conversation.length,20);assert.equal(body.conversation[0].role,'user');assert.equal(body.context.resultSource,'mock');assert.deepEqual(body.context.result,mockResult);return {ok:true,json:async()=>({reply:'This is a sample result.'})};},async()=>{assert.match(await askLifeMap('Why?',Array.from({length:30},()=>({role:'customer',text:'hello'})),{profile:mockProfile,result:mockResult,resultSource:'mock',consent:true}),/sample/);});
 await assert.rejects(askLifeMap('hello'),/privacy notice/);await assert.rejects(askLifeMap('a'.repeat(2001),[],{consent:true}),/2,000/);
});
test('connection and rate-limit failures surface for retry instead of impersonating live AI',async()=>{
 await withFetch(async()=>{throw new TypeError('fetch failed');},async()=>{await assert.rejects(askLifeMap('Hello',[],{consent:true}),/message is saved/);});
 await withFetch(async()=>({ok:false,status:429,json:async()=>({})}),async()=>{await assert.rejects(askLifeMap('Hello',[],{consent:true}),/wait a minute/);});
});
test('sample calculations stay explicit and cannot change the shared fixture',async()=>{
 const response=await calculatePlan({...mockProfile,annualIncome:123456});assert.equal(response.source,'mock');assert.deepEqual(response.result,mockResult);response.result.breakdown.pop();assert.equal(mockResult.breakdown.length,5);
 await assert.rejects(calculatePlan({...mockProfile,mortgageBalance:-1}),/Mortgage balance/);
 assert.throws(()=>validateResult({...mockResult,additionalCoverageNeeded:NaN}),/invalid result/);
});
test('configured calculator and scenario adapters pass profile and changes to backend-owned math',async()=>{
 globalThis.window={location:{hostname:'arnavshergill.github.io'},LIFEMAP_CONFIG:{chatApiUrl:'https://api.example.com/api/chat',calculateApiUrl:'https://api.example.com/api/calculate',scenarioApiUrl:'https://api.example.com/api/scenario'}};
 try{
  const service=await import('../src/services/planService.js?backend-test');
  await withFetch(async(url,options)=>{const body=JSON.parse(options.body);assert.deepEqual(body.profile,mockProfile);if(url.endsWith('/scenario'))assert.deepEqual(body.changes,{mortgageBalance:250000});return {ok:true,json:async()=>({result:mockResult})};},async()=>{assert.equal((await service.calculatePlan(mockProfile)).source,'backend');assert.equal((await service.calculateScenario(mockProfile,'home',{mortgageBalance:250000})).source,'backend');});
 }finally{delete globalThis.window;}
});
