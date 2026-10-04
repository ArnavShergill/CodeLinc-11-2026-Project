// Optional QA helper: point PLAYWRIGHT_MODULE_PATH at an installed Playwright package.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try {
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
 const shot=async name=>{await page.evaluate(()=>scrollTo(0,0));await page.waitForTimeout(250);await page.screenshot({path:`artifacts/${name}.png`,fullPage:true});};
 const go=async route=>{await page.evaluate(r=>{location.hash=r},route);await page.waitForTimeout(250);};
 await page.goto('http://127.0.0.1:5173');await shot('landing-desktop');
 for(const name of ['How It Works','FAQ','See How It Works']){await page.getByRole('button',{name,exact:true}).click();await page.getByRole('button',{name:'Got it'}).click();}
 await page.getByRole('link',{name:'Features',exact:true}).click();await page.locator('#features').waitFor();
 await page.getByRole('link',{name:'Log In',exact:true}).click();await page.getByRole('button',{name:'Settings',exact:true}).click();await page.getByRole('button',{name:'Got it'}).click();await page.getByRole('button',{name:'Open Amos profile'}).click();await page.getByRole('button',{name:'Got it'}).click();
 await page.getByRole('link',{name:'Log Out',exact:true}).click();await page.locator('.nav-actions').getByRole('link',{name:'Get Started',exact:true}).click();await shot('welcome-desktop');
 await page.getByRole('link',{name:'Learn',exact:true}).click();await page.locator('details').first().locator('summary').click();await page.getByRole('button',{name:'Ask a Question',exact:true}).click();await page.locator('#advisor-question').fill('How do policies work?');await page.getByRole('button',{name:'Send question'}).click();await page.getByText('How do policies work?',{exact:true}).waitFor();
 await go('home');await page.locator('#home-question').fill('What does coverage mean?');await page.getByRole('button',{name:'Ask LifeMap',exact:true}).click();await page.getByText('What does coverage mean?',{exact:true}).waitFor();
 await go('home');await page.getByRole('link',{name:'Start My Plan',exact:true}).click();await shot('conversation-desktop');
 await page.locator('#message').fill('My annual income is $75,000');await page.getByRole('button',{name:'Send message'}).click();await page.waitForTimeout(450);
 for(let i=0;i<3;i++){await page.getByRole('button',{name:/Use example:/}).click();await page.waitForTimeout(450)}
 await page.getByRole('link',{name:'Review My Information',exact:true}).click();await shot('review-desktop');
 await page.locator('[data-edit="annualIncome"]').click();await page.locator('#annualIncome').fill('82000');await page.locator('[data-edit="annualIncome"]').click();await page.getByText('$82,000',{exact:true}).waitFor();
 await page.locator('.advanced-profile summary').click();await page.locator('[data-edit="childrenAges"]').click();await page.locator('#childrenAges').fill('7, invalid');await page.getByRole('button',{name:'Calculate My Plan',exact:true}).click();await page.getByRole('alert').filter({hasText:'Children’s ages'}).waitFor();await page.locator('#childrenAges').fill('7, 11');
 await page.getByRole('button',{name:'Calculate My Plan',exact:true}).click();await page.getByText('$650,000',{exact:true}).waitFor();await page.waitForTimeout(450);await shot('results-desktop');
 await page.getByRole('link',{name:'See Full Breakdown',exact:true}).click();await page.getByText('$800,000',{exact:true}).waitFor();await shot('breakdown-desktop');await page.getByRole('link',{name:'Try a life scenario'}).click();
 await page.locator('[data-point="1"] > circle').first().hover();if(!await page.locator('[data-point="1"] .chart-tooltip').isVisible())throw Error('Tooltip not visible');await shot('simulator-desktop');await page.locator('[data-point="1"] > circle').first().click();await page.locator('[data-point="1"]').focus();await page.keyboard.press('Enter');
 for(const [name,value] of [['Have a child','$730,000'],['Buy a home','$820,000'],['Increase income','$750,000'],['Pay off loans','$625,000'],['Get married','$700,000']]){await page.getByRole('button',{name,exact:true}).click();await page.locator('.scenario-comparison strong').filter({hasText:value}).waitFor();}
 await page.getByRole('button',{name:'Reset scenario'}).click();await go('learn');await page.getByRole('button',{name:'Learn the Basics'}).click();await shot('learn-desktop');
 for(const viewport of [{width:1440,height:1000},{width:768,height:1024},{width:390,height:844}]){await page.setViewportSize(viewport);for(const route of ['landing','home','intake','review','results','breakdown','simulator','learn']){await go(route);if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow '+route+' at '+viewport.width);if(viewport.width===390)await shot(route+'-mobile');}}
 await go('home');await page.getByRole('button',{name:'Toggle navigation'}).click();await page.getByRole('link',{name:'Ask LifeMap',exact:true}).click();await page.getByRole('button',{name:'Ask a Question'}).click();await page.getByRole('button',{name:'What is life insurance?',exact:true}).click();await shot('ask-mobile');
 console.log(JSON.stringify({journey:'passed',routes:'8 at desktop/tablet/mobile',mainButtons:'passed',scenarioButtons:5,chartTooltip:'passed',errors},null,2));if(errors.length)process.exitCode=1;
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
