import {mockProfile} from '../data/mockProfile.js';
import {mockResult} from '../data/mockResult.js';
import {validateProfile} from '../types/contracts.js';
import {mockConversation} from '../data/mockConversation.js';
export const intakeQuestions = mockConversation.questions;
const delay = () => new Promise(resolve=>setTimeout(resolve,350));
const API_URL = 'http://127.0.0.1:8000/api/chat';

export async function askLifeMap(message,conversation=[]) {
 if(!message.trim()) throw new Error('Please add a message before sending.');
 let response;
 try {
  response=await fetch(API_URL,{
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({
    message,
    conversation:conversation.map(turn=>({
     role:turn.role==='customer'?'user':turn.role,
     content:turn.text
    }))
   })
  });
 } catch(error) {
  throw new Error('Cannot reach the LifeMap API. Start it with `npm run api`.',{cause:error});
 }
 let payload;
 try {
  payload=await response.json();
 } catch {
  throw new Error('The LifeMap API returned an invalid response.');
 }
 if(!response.ok) throw new Error(payload.error||`The LifeMap API returned HTTP ${response.status}.`);
 if(typeof payload.reply!=='string'||!payload.reply.trim()) {
  throw new Error('The LifeMap API returned an empty reply.');
 }
 return payload.reply;
}

// The reply is live AI; intake profile changes remain clearly synthetic demo values.
export async function sendIntakeMessage({profile,questionIndex,message,conversation=[]}) {
 const reply=await askLifeMap(message,conversation);
 const [field] = intakeQuestions[questionIndex];
 return {profile:{...profile,[field]:mockProfile[field]},reply,source:'live-ai',profileSource:'mock'};
}
// Backend integration: replace with POST LifeNeedsProfile -> LifeNeedsResult.
export async function calculatePlan(profile) {
 const missing = validateProfile(profile);
 if(missing.length) throw new Error(`Please review: ${missing.join(', ')}.`);
 await delay();
 return {result:structuredClone(mockResult),source:'mock'};
}
// AI explanation integration: verified LifeNeedsResult -> explanation; do not change numbers.
export async function explainPlan(result) {
 await delay();
 return `The illustrative ${new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0}).format(result.additionalCoverageNeeded)} result includes income support, outstanding debts, and education needs, with available resources shown separately. This fixed demo estimate does not change when you edit your information.`;
}
