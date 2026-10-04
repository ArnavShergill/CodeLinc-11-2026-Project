import {mockProfile} from '../data/mockProfile.js';
import {mockResult} from '../data/mockResult.js';
import {validateProfile} from '../types/contracts.js';
import {mockConversation} from '../data/mockConversation.js';
export const intakeQuestions = mockConversation.questions;
const delay = () => new Promise(resolve=>setTimeout(resolve,350));
const API_URL = 'http://127.0.0.1:8000/api/chat';

const FALLBACK_PATTERNS = [
 /Could not reach Ollama/i,
 /Start Ollama/i,
 /gemma3:latest/i,
 /fetch failed/i,
 /ERR_CONNECTION_REFUSED/i,
 /ECONNREFUSED/i,
 /HTTP 502/i,
 /HTTP 503/i,
 /local Ollama model/i,
 /The Ollama Python package is not installed/i
];

function isFallbackError(message='') {
 return FALLBACK_PATTERNS.some(pattern => pattern.test(message));
}

function fallbackReply(message='') {
 const cleaned = String(message || '').trim().replace(/\s+/g,' ');
 const lower = cleaned.toLowerCase();
 if(/income|salary|earn|pay/.test(lower)) {
  return 'I\'m in demo mode because the local Ollama service is unavailable. For this sample, the plan assumes a $75,000 annual income and a family-focused protection need.';
 }
 if(/depend|children|family|mortgage|home/.test(lower)) {
  return 'I\'m in demo mode because the local Ollama service is unavailable. This example still reflects a married household with two children and a mortgage alongside other family protection needs.';
 }
 return 'I\'m in demo mode because the local Ollama service is unavailable right now. The app is still running with its sample profile, and starting Ollama with the gemma3:latest model will restore live answers.';
}

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
  return fallbackReply(message);
 }
 let payload;
 try {
  payload=await response.json();
 } catch {
  if(!response.ok) return fallbackReply(message);
  throw new Error('The LifeMap API returned an invalid response.');
 }
 const errorText = payload.error || '';
 if(!response.ok) {
  if(isFallbackError(errorText) || isFallbackError(`HTTP ${response.status}`)) {
   return fallbackReply(message);
  }
  throw new Error(errorText || `The LifeMap API returned HTTP ${response.status}.`);
 }
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
