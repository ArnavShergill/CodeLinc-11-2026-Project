// Public browser configuration. Never put API keys or other secrets here.
// Set this to the HTTPS chat endpoint of your deployed Python backend.
window.LIFEMAP_CONFIG = {
 chatApiUrl: 'https://lifemap-ai-live.vercel.app/api/chat',
 calculateApiUrl: 'https://lifemap-ai-live.vercel.app/api/calculate',
 scenarioApiUrl: 'https://lifemap-ai-live.vercel.app/api/scenario',
 authApiUrl: 'https://lifemap-ai-live.vercel.app/api/auth',
 // Public project URL and publishable key only; never use a service-role key.
 supabaseUrl: '',
 supabasePublishableKey: ''
};
