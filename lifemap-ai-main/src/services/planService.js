import {mockResult} from '../data/mockResult.js';
import {validateProfile} from '../types/contracts.js';
import {mockConversation} from '../data/mockConversation.js';
export const intakeQuestions = mockConversation.questions;
const config=typeof window!=='undefined'?window.LIFEMAP_CONFIG||{}:{};
const hosted=typeof window!=='undefined'&&!['localhost','127.0.0.1','[::1]'].includes(window.location.hostname);
const chatUrl=config.chatApiUrl?.trim()||(hosted?'':'http://127.0.0.1:8000/api/chat');
const intakeUrl=chatUrl?new URL('intake',chatUrl).href:'';
export const calculatorConnected=Boolean(config.calculateApiUrl);
export const scenarioConnected=Boolean(config.scenarioApiUrl);
export const emptyProfile=()=>Object.fromEntries(intakeQuestions.map(([key])=>[key,null]));
export function nextQuestionIndex(profile){return intakeQuestions.findIndex(([key])=>profile[key]==null);}
function validUpdates(updates){
 if(!updates||typeof updates!=='object'||Array.isArray(updates))throw Error('The AI returned invalid profile details.');
 const valid={};
 for(const [key,value] of Object.entries(updates)){
  if(!intakeQuestions.some(([field])=>field===key)||value==null)continue;
  const partial={...Object.fromEntries(intakeQuestions.map(([field])=>[field,field==='childrenAges'?[]:0])),[key]:value};
  if(validateProfile(partial).length)throw Error('The AI returned invalid details. Please rephrase your answer.');
  valid[key]=value;
 }
 return valid;
}
async function post(url,body){
 if(!url)throw Error('Live AI is not connected. You can review your details or use the sample profile.');
 if(hosted&&!url.startsWith('https://'))throw Error('The hosted LifeMap backend must use HTTPS.');
 let response;
 try{response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(100000)});}
 catch(error){throw Error(error.name==='TimeoutError'?'The request timed out. Your message is saved; please retry.':'Could not reach the LifeMap AI backend. Your message is saved; please retry.');}
 let payload;
 try{payload=await response.json();}catch{throw Error('The backend returned an invalid response. Please retry.');}
 if(!response.ok)throw Error(response.status===429?'Too many requests. Please wait a minute and retry.':response.status===400?(payload.error||'Please check your information.'):'The LifeMap AI backend is unavailable. Please retry.');
 return payload;
}
function requestBody(message,conversation,context){
 if(typeof message!=='string'||!message.trim()||message.length>2000)throw Error('Please send between 1 and 2,000 characters.');
 const details=context;
 return {message,context:details,conversation:conversation.slice(-20).map(turn=>({role:turn.role==='customer'?'user':turn.role,content:turn.text}))};
}
export async function askLifeMap(message,conversation=[],context={}){
 const payload=await post(chatUrl,requestBody(message,conversation,context));
 if(typeof payload.reply!=='string'||!payload.reply.trim())throw Error('The AI returned an empty answer. Please retry.');
 return payload.reply;
}
export async function sendIntakeMessage({profile,questionIndex,message,conversation=[]}){
 const field=intakeQuestions[questionIndex]?.[0]||null;
 const payload=await post(intakeUrl,{...requestBody(message,conversation,{profile}),field});
 if(typeof payload.reply!=='string')throw Error('The AI returned an invalid answer. Please retry.');
 return {updates:validUpdates(payload.updates),reply:payload.reply};
}
export function validateResult(result){
 if(!result||['immediateNeeds','longTermNeeds','totalNeeds','availableResources','additionalCoverageNeeded'].some(key=>typeof result[key]!=='number'||!Number.isFinite(result[key])||result[key]<0)
 ||!Array.isArray(result.breakdown)||result.breakdown.some(item=>typeof item.label!=='string'||typeof item.amount!=='number'||!Number.isFinite(item.amount)||item.amount<0)
 ||!Array.isArray(result.assumptions)||result.assumptions.some(item=>typeof item!=='string'))throw Error('The calculator returned an invalid result.');
 return result;
}
export async function calculatePlan(profile){
 const missing=validateProfile(profile);
 if(missing.length)throw Error(`Please review: ${missing.join(', ')}.`);
 if(config.calculateApiUrl){const payload=await post(config.calculateApiUrl,{profile});return {result:validateResult(payload.result),source:'backend'};}
 return {result:structuredClone(mockResult),source:'mock'};
}
export async function calculateScenario(profile,scenario,changes,options={}){
 if(!config.scenarioApiUrl)throw Error('Live scenarios are waiting for the calculator integration.');
 const payload=await post(config.scenarioApiUrl,{profile,scenario,changes,...options});
 validateResult(payload.result);
 if(!Array.isArray(payload.timeline)||payload.timeline.length!==5||payload.timeline.some(point=>['year','additionalNeed','proposedCoverage','remainingGap'].some(key=>typeof point[key]!=='number'||!Number.isFinite(point[key])||point[key]<0)))throw Error('The simulator returned an invalid timeline.');
 return {...payload,result:payload.result,source:'backend'};
}
export async function generateLesson(topic,context={}){
 const payload=await post(new URL('lesson',chatUrl).href,{topic,context});
 const lesson=payload.lesson;
 if(!lesson||['title','explanation','example','question','why'].some(key=>typeof lesson[key]!=='string')||!Array.isArray(lesson.choices)||lesson.choices.length!==3||lesson.choices.some(choice=>typeof choice!=='string')||!Number.isInteger(lesson.correctIndex)||lesson.correctIndex<0||lesson.correctIndex>2)throw Error('The tutor returned an invalid lesson. Please retry.');
 return lesson;
}
export async function explainPlan(result,profile,source='mock',details={}){
 if(source==='mock')return 'This is a fixed sample result used to preview the experience. It is not calculated from your information. Your team is connecting the Lincoln calculators; your personal estimate will be available after that integration.';
 return askLifeMap('Explain the provided calculator result in plain language. Use its numbers exactly and describe the main contributors. Do not recalculate anything.',[],{...details,profile,result,resultSource:source});
}
