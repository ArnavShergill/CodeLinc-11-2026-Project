// Run with PLAYWRIGHT_MODULE_PATH if Playwright is installed outside this project.
// QA_STATIC_ROOT serves the local app at the production Pages origin for browser QA.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const path=require('path');
const assert=require('assert/strict');
const referenceResult=require('./fixtures/reference-result.json');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  if(process.env.QA_STATIC_ROOT)await page.route('https://arnavshergill.github.io/**',route=>{
   const relative=new URL(route.request().url()).pathname.replace('/CodeLinc-11-2026-Project/','')||'index.html';
   return route.fulfill({path:path.join(process.env.QA_STATIC_ROOT,relative)});
  });
  let failNext=false,intakeCalls=0,advisorCalls=0,lastAdvisor,calculationCalls=0,scenarioCalls=0,lessonCalls=0;
  await page.route('**/api/intake',async route=>{
   intakeCalls++;const body=route.request().postDataJSON();
   if(failNext){failNext=false;return route.fulfill({status:502,json:{error:'Unavailable'}});}
   const updates=body.message.includes('correction')?{annualIncome:95000}:body.field==='annualIncome'?{annualIncome:90000,numberOfDependents:2}:{spouseAnnualIncome:45000};
   return route.fulfill({json:{reply:'Please confirm these details.',updates}});
  });
  await page.route('**/api/chat',async route=>{
   advisorCalls++;lastAdvisor=route.request().postDataJSON();
   return route.fulfill({json:{reply:'Your confirmed annual income is '+lastAdvisor.context.profile.annualIncome+'. Calculations are still examples.'}});
  });
  await page.route('**/api/calculate',async route=>{
   calculationCalls++;const body=route.request().postDataJSON();
   const result=structuredClone(referenceResult);
   if(body.profile.mortgageBalance===220000){result.additionalCoverageNeeded=630375.55;result.totalNeeds=780375.55;result.immediateNeeds=260000;result.breakdown[0].amount=220000;}
   await route.fulfill({json:{result}});
  });
  await page.route('**/api/scenario',async route=>{
   scenarioCalls++;const body=route.request().postDataJSON();const result=structuredClone(referenceResult);
   const amount=body.changes?.mortgageBalance===250000?660375.55:630375.55;
   result.additionalCoverageNeeded=amount;
   await route.fulfill({json:{scenario:body.scenario,result,changes:body.changes||{},proposedCoverage:body.proposedCoverage,policyYears:body.policyYears,
    timeline:[0,5,10,15,20].map(year=>({year,additionalNeed:year===0?amount:150000,proposedCoverage:year<body.policyYears?body.proposedCoverage:0,remainingGap:year<body.policyYears?Math.max(0,(year===0?amount:150000)-body.proposedCoverage):150000})),
    assumptions:['Conditional planning illustration; no automatic loan payoff.']}});
  });
  await page.route('**/api/lesson',async route=>{
   lessonCalls++;const body=route.request().postDataJSON();assert.equal(body.topic,'protection');
   await route.fulfill({json:{lesson:{title:'Who life insurance helps',explanation:'A payable death benefit can help beneficiaries with financial responsibilities.',example:'Income support can help financial dependents.',question:'Who receives the payable death benefit?',choices:['Beneficiaries','Everyone immediately','The insured person automatically'],correctIndex:0,why:'The payable death benefit supports beneficiaries.',topic:'protection'}}});
  });
  await page.goto(process.env.QA_BASE_URL||(process.env.QA_STATIC_ROOT?'https://arnavshergill.github.io/CodeLinc-11-2026-Project/':'http://127.0.0.1:5173'));
  const go=async route=>{await page.evaluate(r=>location.hash=r,route);await page.waitForTimeout(150);};
  await go('learn');await page.getByRole('button',{name:'Start my first lesson'}).click();
  await page.getByRole('heading',{name:'Who life insurance helps',exact:true}).waitFor();
  await page.getByRole('button',{name:'Beneficiaries',exact:true}).click();await page.getByText('You’ve got it.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Explain this more simply with AI'}).click();await page.getByRole('button',{name:'Send question'}).waitFor();
  await page.waitForFunction(()=>document.querySelectorAll('.advisor-messages .message.assistant').length>0);
  await go('intake');
  await page.locator('#message').fill('I earn 90k and support two people');
  await page.getByRole('button',{name:'Send message'}).click();
  await page.getByRole('button',{name:'Confirm details'}).waitFor();
  assert.equal(await page.locator('.captured-row').count(),0);
  await page.getByRole('button',{name:'Confirm details'}).click();
  await page.locator('.captured').getByText('$90,000',{exact:true}).waitFor();
  assert.equal(await page.locator('.captured-row').count(),2);
  await page.locator('#message').fill('correction: annual income is 95k');
  await page.getByRole('button',{name:'Send message'}).click();
  await page.getByRole('button',{name:'Let me correct that'}).click();
  await page.locator('.captured').getByText('$90,000',{exact:true}).waitFor();
  await page.locator('#message').fill('correction: annual income is 95k');
  await page.getByRole('button',{name:'Send message'}).click();
  await page.getByRole('button',{name:'Confirm details'}).click();
  await page.locator('.captured').getByText('$95,000',{exact:true}).waitFor();
  failNext=true;await page.locator('#message').fill('45000');await page.getByRole('button',{name:'Send message'}).click();
  await page.getByRole('button',{name:'Retry message'}).waitFor();
  const turns=await page.locator('.message.customer').count();
  await page.getByRole('button',{name:'Retry message'}).click();await page.getByRole('button',{name:'Confirm details'}).click();
  assert.equal(await page.locator('.message.customer').count(),turns);
  await go('learn');await page.getByRole('button',{name:'Ask a Question',exact:true}).click();
  await page.locator('#advisor-question').fill('What information do you have?');await page.getByRole('button',{name:'Send question'}).click();
  await page.getByText('Your confirmed annual income is 95000. Calculations are still examples.',{exact:true}).waitFor();
  assert.equal(lastAdvisor.context.profile.annualIncome,95000);
  await go('review');assert.equal(await page.locator('#annualIncome').inputValue(),'95000');
  await go('intake');await page.getByRole('button',{name:'Use a complete sample profile instead'}).click();
  await page.getByRole('link',{name:'Review My Information',exact:true}).click();
  await page.getByRole('button',{name:'Calculate My Plan'}).click();await page.getByText('Estimated Coverage Needed',{exact:true}).waitFor();
  await page.locator('.big-number').getByText('$590,376',{exact:true}).waitFor();
  await go('review');await page.locator('[data-edit="mortgageBalance"]').click();await page.locator('#mortgageBalance').fill('220000');await page.locator('[data-edit="mortgageBalance"]').click();
  await page.getByRole('button',{name:'Calculate My Plan'}).click();await page.locator('.big-number').getByText('$630,376',{exact:true}).waitFor();
  await go('simulator');await page.locator('.projection-table').waitFor();
  const protectionUpdate=page.waitForResponse(response=>response.url().endsWith('/api/scenario'));
  await page.getByRole('button',{name:'Update protection view',exact:true}).click();await protectionUpdate;
  await page.getByRole('button',{name:'Update protection view',exact:true}).waitFor({state:'visible'});
  await page.getByRole('button',{name:'Buy a home',exact:true}).click();await page.locator('#scenario-form input[name="mortgageBalance"]').fill('250000');
  await page.getByRole('button',{name:'Apply changes to my projection'}).click();await page.locator('.scenario-comparison').getByText('$660,376',{exact:true}).waitFor();
  const futureReply=page.waitForResponse(response=>response.url().endsWith('/api/chat'));
  await page.getByRole('button',{name:'Explain this future view with AI'}).click();await futureReply;
  assert.equal(lastAdvisor.context.simulation.changes.mortgageBalance,250000);
  assert.equal(lastAdvisor.context.profile.mortgageBalance,220000);

  for(const viewport of [{width:1440,height:1000},{width:768,height:1024},{width:390,height:844}]){
   await page.setViewportSize(viewport);
   for(const route of ['landing','home','intake','review','results','breakdown','simulator','learn']){
    await go(route);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Overflow '+route+' at '+viewport.width);
   }
  }
  await go('intake');await page.getByRole('button',{name:'Clear my details and conversation'}).click();
  assert.equal(await page.locator('.captured-row').count(),0);assert.equal(await page.locator('.message.customer').count(),0);
  assert.equal(await page.locator('input[type="checkbox"]').count(),0);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({confirmation:'passed',corrections:'passed',retry:'passed',privacy:'passed',context:'passed',personalizedCalculations:'passed',lessonQuiz:'passed',scenarioContext:'passed',calculationCalls,scenarioCalls,lessonCalls,routes:'8 at desktop/tablet/mobile',intakeCalls,advisorCalls,errors},null,2));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
