// Real local account HTTP/database/browser test. Synthetic identities only.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE_PATH||'playwright');
const {spawn}=require('child_process');const readline=require('readline');const {once}=require('events');
const path=require('path');const fs=require('fs');const os=require('os');const assert=require('assert/strict');
const root=path.resolve(__dirname,'../..');const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'lifemap-account-browser-'));
const server=spawn(process.env.AUDIT_PYTHON||'python3',['-u','-c',`
import json
from http.server import ThreadingHTTPServer
from api_server import LifeMapAPIHandler
server=ThreadingHTTPServer(('127.0.0.1',0),LifeMapAPIHandler)
print(json.dumps({'port':server.server_port}),flush=True)
server.serve_forever()
`],{cwd:root,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1',VERCEL:'',DATABASE_URL:'',POSTGRES_URL:'',LIFEMAP_AUTH_REQUIRE_POSTGRES:'',LIFEMAP_AUTH_DB_PATH:path.join(temporary,'accounts.sqlite3')},stdio:['ignore','pipe','inherit']});
(async()=>{
 let browser;
 try{
  const lines=readline.createInterface({input:server.stdout});const [line]=await once(lines,'line');const {port}=JSON.parse(line);
  const api='http://127.0.0.1:'+port;const browserApi='https://account-api.example.test';
  browser=await chromium.launch({channel:'chrome',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const origin='https://arnavshergill.github.io';
  const preflight=await page.request.fetch(api+'/api/auth',{method:'OPTIONS',headers:{Origin:origin,'Access-Control-Request-Headers':'Content-Type, Authorization'}});
  assert.equal(preflight.status(),204);assert.ok(preflight.headers()['access-control-allow-headers'].includes('Authorization'));
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.route('https://arnavshergill.github.io/**',route=>{const relative=new URL(route.request().url()).pathname.replace('/CodeLinc-11-2026-Project/','')||'index.html';return route.fulfill({path:path.join(root,'lifemap-ai-main',relative)});});
  await page.route('**/config.js',route=>route.fulfill({contentType:'application/javascript',body:`window.LIFEMAP_CONFIG={authApiUrl:'${browserApi}/api/auth'};`}));
  let accountCalls=0;
  await page.route(browserApi+'/api/auth',async route=>{
   accountCalls++;const response=await page.request.post(api+'/api/auth',{data:route.request().postDataJSON(),headers:{Origin:origin,...(route.request().headers().authorization?{Authorization:route.request().headers().authorization}:{})}});
   assert.equal(response.headers()['cache-control'],'no-store');
   assert.equal(response.headers()['access-control-allow-origin'],origin);
   return route.fulfill({status:response.status(),body:await response.body(),contentType:'application/json'});
  });
  const responseFor=action=>page.waitForResponse(response=>response.url().endsWith('/api/auth')&&response.request().postDataJSON().action===action);
  const fillLogin=async password=>{await page.locator('#account-email').fill('jordan@example.test');await page.locator('#account-password').fill(password);};
  await page.goto('https://arnavshergill.github.io/CodeLinc-11-2026-Project/');
  await page.getByRole('link',{name:'Get Started',exact:true}).click();await page.locator('#account-form').waitFor();
  assert.equal(await page.getByRole('button',{name:'Create account',exact:true}).isEnabled(),true);
  await page.locator('#full-name').fill('Jordan Taylor');await fillLogin('Synthetic-long-password-123');
  let pending=responseFor('register');await page.getByRole('button',{name:'Create account',exact:true}).click();
  const registration=await (await pending).json();await page.getByRole('heading',{name:'Welcome, Jordan',exact:true}).waitFor();
  assert.equal(registration.user.user_metadata.full_name,'Jordan Taylor');assert.ok(!JSON.stringify(registration).includes('password'));
  const stored=await page.evaluate(()=>JSON.stringify({...sessionStorage}));assert.ok(!stored.includes('Synthetic-long-password-123'));assert.ok(!stored.includes('jordan@example.test'));
  pending=responseFor('session');await page.reload();assert.equal((await pending).status(),200);await page.getByRole('heading',{name:'Welcome, Jordan',exact:true}).waitFor();
  pending=responseFor('logout');await page.getByRole('button',{name:'End session',exact:true}).click();assert.equal((await pending).status(),200);await page.locator('.public-nav').waitFor();
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('lifemap-auth')),null);
  const revoked=await page.request.post(api+'/api/auth',{data:{action:'session'},headers:{Authorization:'Bearer '+registration.access_token}});assert.equal(revoked.status(),401);
  await page.locator('.login-link').click();await fillLogin('Wrong-synthetic-password');pending=responseFor('login');await page.getByRole('button',{name:'Log in',exact:true}).click();assert.equal((await pending).status(),401);await page.getByRole('alert').filter({hasText:'Email or password is incorrect'}).waitFor();
  await fillLogin('Synthetic-long-password-123');pending=responseFor('login');await page.getByRole('button',{name:'Log in',exact:true}).click();assert.equal((await pending).status(),200);await page.getByRole('heading',{name:'Welcome, Jordan',exact:true}).waitFor();
  // Re-registration cannot replace an existing account or its password.
  pending=responseFor('logout');await page.getByRole('button',{name:'End session',exact:true}).click();await pending;await page.locator('.public-nav').waitFor();
  await page.getByRole('link',{name:'Get Started',exact:true}).click();await page.locator('#full-name').fill('Different Name');await fillLogin('Different-long-password-456');
  pending=responseFor('register');await page.getByRole('button',{name:'Create account',exact:true}).click();assert.equal((await pending).status(),409);await page.getByRole('alert').filter({hasText:'Try logging in'}).waitFor();
  // A forged stored session must be removed, not trusted for a greeting.
  await page.evaluate(()=>sessionStorage.setItem('lifemap-auth',JSON.stringify({token:'a'.repeat(43),expires:Date.now()+100000})));
  pending=responseFor('session');await page.reload();assert.equal((await pending).status(),401);await page.waitForFunction(()=>!sessionStorage.getItem('lifemap-auth'));
  assert.equal(await page.locator('#account-password').inputValue(),'');assert.deepEqual(errors,[]);
  console.log(JSON.stringify({realSignup:'PASS',persistentLogin:'PASS',reloadValidation:'PASS',serverLogout:'PASS',wrongPassword:'PASS',duplicateEmail:'PASS',forgedSession:'PASS',noStoredPasswords:'PASS',accountCalls,errors},null,2));
 }finally{if(browser)await browser.close();server.kill('SIGTERM');await once(server,'exit').catch(()=>{});fs.rmSync(temporary,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
