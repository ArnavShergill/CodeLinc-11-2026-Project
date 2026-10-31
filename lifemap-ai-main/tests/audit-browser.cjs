// Real Python HTTP calculator + real UI; only model generation is stubbed.
// Synthetic fixtures only. No model, key, or external financial-data transmission.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {spawn}=require('child_process');const readline=require('readline');
const {once}=require('events');const path=require('path');const assert=require('assert/strict');
const root=path.resolve(__dirname,'../..');
const server=spawn(process.env.AUDIT_PYTHON||'python3',['-u','-c',`
import json
from http.server import ThreadingHTTPServer
import AI_interact as ai, chat_features, api_server
from calculator_bridge import calculate
fixture={k:v for k,v in ai.get_demo_profile().items() if k in ai.REQUIRED_PROFILE_FIELDS}
fixture['childrenAges']=[]
def model(messages,**kwargs):
 if 'Extract' in messages[0]['content']:return json.dumps(fixture)
 return 'The result reflects the needs and resources you supplied.'
ai._chat=model
chat_features._chat=model
ai._educational_reply=lambda *args:'Life insurance can support the people you choose after a covered death.'
class Handler(api_server.LifeMapAPIHandler):
 def do_POST(self):
  api_server._requests.clear() # Isolate functionality from the separately unit-tested burst guard.
  return super().do_POST()
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
print(json.dumps({'port':server.server_port,'profile':fixture,'result':calculate(fixture)}),flush=True)
server.serve_forever()
`],{cwd:root,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},stdio:['ignore','pipe','inherit']});
(async()=>{
 const lines=readline.createInterface({input:server.stdout});const [line]=await once(lines,'line');const fixture=JSON.parse(line);const api='http://127.0.0.1:'+fixture.port;const browserApi='https://audit-api.example.test';
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('https://arnavshergill.github.io/**',route=>{const relative=new URL(route.request().url()).pathname.replace('/CodeLinc-11-2026-Project/','')||'index.html';return route.fulfill({path:path.join(root,'lifemap-ai-main',relative)});});
  await page.route('**/config.js',r=>r.fulfill({contentType:'application/javascript',body:`window.LIFEMAP_CONFIG={chatApiUrl:'${browserApi}/api/chat',calculateApiUrl:'${browserApi}/api/calculate',scenarioApiUrl:'${browserApi}/api/scenario'};`}));
  let scenarioCalls=0,calculateCalls=0,failScenario=false,lastScenario,lastChat;
  await page.route(browserApi+'/api/**',async route=>{
   const pathname=new URL(route.request().url()).pathname;const body=route.request().postDataJSON();
   if(pathname==='/api/scenario'){scenarioCalls++;lastScenario=body;if(failScenario){failScenario=false;return route.fulfill({status:502,json:{error:'Synthetic failed request'}});}}
   if(pathname==='/api/calculate')calculateCalls++;
   if(pathname==='/api/chat')lastChat=body;
   const response=await page.request.post(api+pathname,{data:body});return route.fulfill({status:response.status(),body:await response.body(),contentType:'application/json'});
  });
  const go=async route=>{await page.evaluate(r=>location.hash=r,route);await page.waitForTimeout(100);};
  const usd=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(n);
  await page.goto('https://arnavshergill.github.io/CodeLinc-11-2026-Project/#intake');
  await page.locator('#message').fill('Synthetic test: mortgage 180k, other debt 25k, final expenses 15k, annual family support 50k for ten years, education 80k, insurance 100k, assets 50k.');
  await page.getByRole('button',{name:'Send message',exact:true}).click();await page.getByRole('button',{name:'Confirm details',exact:true}).waitFor();
  assert.equal(await page.locator('.captured-row').count(),0);await page.getByRole('button',{name:'Confirm details',exact:true}).click();
  await go('review');await page.getByRole('button',{name:'Calculate My Plan',exact:true}).click();await page.locator('.big-number').waitFor();
  assert.equal(await page.locator('.big-number').innerText(),usd(fixture.result.additionalCoverageNeeded));assert.equal(calculateCalls,1);
  await go('breakdown');assert.match(await page.locator('.final-total').innerText(),/590,376/);
  await go('simulator');await page.locator('.projection-table').waitFor();
  const cases=[['Have a child','child',{numberOfDependents:4,collegeFundingNeed:100000,desiredAnnualIncome:55000},1],
   ['Buy a home','home',{mortgageBalance:250000},1],['Increase income','income',{annualIncome:100000,desiredAnnualIncome:60000},1],
   ['Pay off loans','debt',{otherDebt:0},-1],['Get married','married',{spouseAnnualIncome:60000,desiredAnnualIncome:55000},1]];
  for(const [label,id,changes,direction] of cases){
   await page.getByRole('button',{name:label,exact:true}).click();
   for(const [key,value] of Object.entries(changes))await page.locator('#scenario-form input[name="'+key+'"]').fill(String(value));
   const count=scenarioCalls;const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/scenario')&&r.request().postDataJSON().scenario===id);
   await page.getByRole('button',{name:'Apply changes to my projection',exact:true}).click();const response=await responsePromise;const data=await response.json();
   await page.getByRole('button',{name:'Apply changes to my projection',exact:true}).waitFor();await page.waitForFunction(()=>!document.querySelector('#scenario-form button').disabled);
   assert.equal(scenarioCalls,count+1);assert.equal(response.status(),200);assert.deepEqual(lastScenario.changes,changes);
   assert.deepEqual(data.profile,{...fixture.profile,...changes});assert.deepEqual(data.baseResult,fixture.result);
   assert.ok(direction*(data.result.additionalCoverageNeeded-fixture.result.additionalCoverageNeeded)>0);
   for(const [key,value] of Object.entries(changes))assert.equal(await page.locator('#scenario-form input[name="'+key+'"]').inputValue(),String(value));
   const comparison=await page.locator('.scenario-comparison').innerText();assert.ok(comparison.includes(usd(fixture.result.additionalCoverageNeeded)));assert.ok(comparison.includes(usd(data.result.additionalCoverageNeeded)));
   assert.ok((await page.locator('.chart-card svg').getAttribute('aria-label')).includes(usd(data.timeline[0].additionalNeed)));
   assert.ok((await page.locator('.projection-table tbody tr').first().innerText()).includes(usd(data.timeline[0].remainingGap)));
   assert.equal(await page.locator('.coverage-line').evaluate(e=>getComputedStyle(e).stroke),'rgb(161, 93, 25)');
   await page.getByRole('button',{name:'Explain this future view with AI',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.advisor .message.assistant').length>0);
   assert.deepEqual(lastChat.context.simulation.changes,changes);assert.equal(lastChat.context.profile.mortgageBalance,fixture.profile.mortgageBalance);
   await go('simulator');assert.ok((await page.locator('.scenario-comparison').innerText()).includes(usd(data.result.additionalCoverageNeeded)));
   await page.getByRole('button',{name:'Back to my original situation',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('#protection-form button').disabled);
  }
  // Failure/retry must replay the failed edit, not revert to baseline.
  await page.getByRole('button',{name:'Buy a home',exact:true}).click();await page.locator('#scenario-form input[name=mortgageBalance]').fill('300000');failScenario=true;
  await page.getByRole('button',{name:'Apply changes to my projection',exact:true}).click();await page.getByRole('button',{name:'Retry projection',exact:true}).waitFor();
  assert.equal(await page.locator('#scenario-form input[name=mortgageBalance]').inputValue(),'300000');await page.getByRole('button',{name:'Retry projection',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('#scenario-form button').disabled);
  assert.equal(lastScenario.changes.mortgageBalance,300000);
  // Updating policy controls must keep the applied scenario and the original plan.
  await page.locator('#protection-form input[name=coverage]').fill('300000');await page.locator('#protection-form input[name=years]').fill('10');
  await page.getByRole('button',{name:'Update protection view',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('#protection-form button').disabled);
  assert.equal(lastScenario.changes.mortgageBalance,300000);assert.equal(lastScenario.proposedCoverage,300000);assert.equal(lastScenario.policyYears,10);
  await go('results');assert.equal(await page.locator('.big-number').innerText(),usd(fixture.result.additionalCoverageNeeded));
  // Review blank optional assumptions must preserve backend defaults, not submit zero.
  await go('review');await page.getByRole('button',{name:'Calculate My Plan',exact:true}).click();await page.locator('.big-number').waitFor();assert.equal(await page.locator('.big-number').innerText(),usd(fixture.result.additionalCoverageNeeded));
  await go('review');await page.locator('[data-edit=mortgageBalance]').click();await page.locator('#mortgageBalance').fill('220000');await page.locator('[data-edit=mortgageBalance]').click();
  await page.getByRole('button',{name:'Calculate My Plan',exact:true}).click();await page.locator('.big-number').waitFor();assert.equal(await page.locator('.big-number').innerText(),usd(fixture.result.additionalCoverageNeeded+40000));
  await go('simulator');await page.locator('.projection-table').waitFor();assert.equal(lastScenario.proposedCoverage,fixture.result.additionalCoverageNeeded+40000);assert.deepEqual(lastScenario.changes,{});
  await go('review');await page.locator('[data-edit=mortgageBalance]').click();await page.locator('#mortgageBalance').fill('');await page.locator('[data-edit=mortgageBalance]').click();
  assert.equal(await page.locator('#mortgageBalance').getAttribute('aria-invalid'),'true');assert.equal(await page.locator('#mortgageBalance').inputValue(),'');
  await page.locator('#mortgageBalance').fill('220000');await page.locator('[data-edit=mortgageBalance]').click();
  await page.locator('details.advanced-profile').evaluate(e=>e.open=true);await page.locator('#inflationRate').fill('2.75');await page.locator('[data-edit=inflationRate]').click();
  assert.equal(await page.locator('#inflationRate').locator('..').locator('.formatted-value').innerText(),'2.75%');
  const expectedResponse=await page.request.post(api+'/api/calculate',{data:{profile:{...fixture.profile,mortgageBalance:220000,inflationRate:.0275}}});const expected=await expectedResponse.json();
  await page.getByRole('button',{name:'Calculate My Plan',exact:true}).click();await page.locator('.big-number').waitFor();assert.equal(await page.locator('.big-number').innerText(),usd(expected.result.additionalCoverageNeeded));
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({realCalculatorHTTP:'PASS',requiredOnlyReview:'PASS',allFiveScenarios:'PASS',appliedInputsRetained:'PASS',retryRetainsChanges:'PASS',chartAndLegend:'PASS',AIContextAndExplanation:'PASS',baselinePreserved:'PASS',editAndRecalculate:'PASS',invalidBlankEdit:'PASS',rateRoundTrip:'PASS',calculateCalls,scenarioCalls,errors},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>server.kill());
