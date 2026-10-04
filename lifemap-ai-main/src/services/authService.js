// Account credentials go only to the account endpoint, never to AI.
const config=typeof window==='undefined'?{}:window.LIFEMAP_CONFIG||{};
const base=(config.supabaseUrl||'').replace(/\/$/,'');
const key=config.supabasePublishableKey||'';
// Retain compatibility with an explicitly configured Supabase deployment.
const managed=Boolean(!config.authApiUrl&&base.startsWith('https://')&&key);
const accountEndpoint=config.authApiUrl||(!managed&&typeof window!=='undefined'?new URL('/api/auth',window.location.href).href:'');
function validEndpoint(value){try{const url=new URL(value);return url.protocol==='https:'||(url.protocol==='http:'&&['localhost','127.0.0.1'].includes(url.hostname));}catch{return false;}}
export const authConfigured=managed||validEndpoint(accountEndpoint);
let token='';
async function request(path,body,method='POST'){
 if(!authConfigured)throw Error('Account registration is not connected yet. Please try again after setup.');
 const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),20000);
 const action={signup:'register','token?grant_type=password':'login',user:'session',logout:'logout'}[path];
 const payload=managed?body:{action,...(path==='signup'?{fullName:body.data.full_name,email:body.email,password:body.password}:body||{})};
 try{const response=await fetch(managed?base+'/auth/v1/'+path:accountEndpoint,{method:managed?method:'POST',headers:{...(managed?{apikey:key}:{}),'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},...(payload?{body:JSON.stringify(payload)}:{}),signal:controller.signal});
 const data=await response.json().catch(()=>({}));
 if(!response.ok){const error=Error(data.error||data.msg||data.error_description||data.message||'Could not complete that request. Please try again.');error.status=response.status;throw error;}return data;
 }catch(error){if(error.name==='AbortError'||error instanceof TypeError)throw Error('Could not connect to accounts. Please try again.');throw error;}finally{clearTimeout(timeout);}
}
function keepSession(data){if(!data.access_token)return null;token=data.access_token;try{sessionStorage.setItem('lifemap-auth',JSON.stringify({token,expires:Date.now()+(data.expires_in||3600)*1000}));}catch{}return data.user;}
export async function createAccount(fullName,email,password){const data=await request('signup',{email,password,data:{full_name:fullName}});return {user:keepSession(data),confirmationRequired:!data.access_token};}
export async function login(email,password){return keepSession(await request('token?grant_type=password',{email,password}));}
function clearSession(){token='';try{sessionStorage.removeItem('lifemap-auth');sessionStorage.removeItem('lifemap-first-name');}catch{}}
export async function restoreAccount(){try{const stored=JSON.parse(sessionStorage.getItem('lifemap-auth')||'null');if(!stored||stored.expires<=Date.now()||!authConfigured){clearSession();return null;}token=stored.token;const data=await request('user',null,'GET');return managed?data:data.user;}catch(error){if(error.status===401)clearSession();return null;}}
export async function logout(){try{if(token)await request('logout');}finally{clearSession();}}
