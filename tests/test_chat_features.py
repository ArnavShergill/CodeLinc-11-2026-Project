import io
import json
import unittest
import AI_interact
from unittest.mock import patch
from chat_features import clean_profile, clean_context, capture_intake
from api_server import LifeMapAPIHandler, allow_request, _requests


class ChatTests(unittest.TestCase):
    def test_profile_validation_and_unknown_fields(self):
        self.assertEqual(clean_profile({'annualIncome': 90000, 'password': 'secret', 'otherDebt': None}), {'annualIncome': 90000})
        for value in [{'annualIncome': -1}, {'numberOfDependents': True}, {'childrenAges': [121]}, {'inflationRate': 2}]:
            with self.assertRaises(ValueError): clean_profile(value)

    def test_capture_returns_changes_for_confirmation_only(self):
        profile = {'annualIncome': 75000}
        with patch('chat_features._chat', return_value='{"annualIncome":90000,"numberOfDependents":2}'):
            result = capture_intake('Actually I earn 90k and support two people', profile, 'otherDebt')
        self.assertEqual(result['updates'], {'annualIncome': 90000, 'numberOfDependents': 2})
        self.assertEqual(profile['annualIncome'], 75000)
        with patch('chat_features._chat', return_value='{}'):
            self.assertEqual(capture_intake('What does that mean?', {}, 'annualIncome')['updates'], {})

    def test_invalid_extraction_never_becomes_a_fact(self):
        with patch('chat_features._chat', return_value='{"annualIncome":-100}'):
            with self.assertRaises(RuntimeError): capture_intake('hello', {}, 'annualIncome')

    def test_cloud_requests_omit_unsupported_structured_output_flag(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"message":{"content":"{}"}}'
        with patch.object(AI_interact, 'OLLAMA_URL', 'https://ollama.com/api/chat'), patch.object(AI_interact, 'urlopen', return_value=Response()) as request:
            self.assertEqual(AI_interact._chat([], json_mode=True), '{}')
            self.assertNotIn('format', json.loads(request.call_args.args[0].data))
        with patch('chat_features._chat', return_value='```json\n{"annualIncome":90000}\n```'):
            self.assertEqual(capture_intake('90k', {}, 'annualIncome')['updates'], {'annualIncome':90000})

    def test_context_preserves_calculator_source(self):
        self.assertEqual(clean_context({'profile': {'annualIncome': 90000}, 'resultSource': 'mock'})['resultSource'], 'mock')
        with self.assertRaises(ValueError): clean_context({'result': {'totalNeeds': 'pretend'}})

    def test_burst_limit_expires(self):
        _requests.clear()
        for _ in range(20): self.assertTrue(allow_request('test', now=100))
        self.assertFalse(allow_request('test', now=100))
        self.assertTrue(allow_request('test', now=161))
        _requests.clear()

    def request(self, body, path='/api/chat', origin='https://arnavshergill.github.io'):
        raw=json.dumps(body).encode()
        handler=object.__new__(LifeMapAPIHandler)
        handler.path=path
        handler.headers={'Content-Length':str(len(raw)), 'Origin':origin, 'Host':'api.example.com'}
        handler.client_address=('test', 1234)
        handler.rfile=io.BytesIO(raw)
        output=[]
        handler._send_json=lambda status,payload:output.append((status,payload))
        handler.do_POST()
        return output[0]

    def test_http_rejects_no_consent_bad_origin_and_oversized_messages(self):
        self.assertEqual(self.request({'message':'hello'})[0],400)
        self.assertEqual(self.request({'message':'hello','consent':True},origin='https://evil.example')[0],403)
        self.assertEqual(self.request({'message':'x'*2001,'consent':True})[0],400)

    def test_http_passes_context_and_hides_provider_errors(self):
        body={'message':'hello','consent':True,'context':{'profile':{'annualIncome':90000}}}
        with patch('api_server.API_request',return_value='Answer') as model:
            self.assertEqual(self.request(body),(200,{'reply':'Answer'}))
            self.assertEqual(model.call_args.args[2]['profile'],{'annualIncome':90000})
        with patch('api_server.API_request',side_effect=RuntimeError('secret-provider-details')):
            status,payload=self.request(body)
            self.assertEqual(status,502)
            self.assertNotIn('secret-provider-details',str(payload))

if __name__=='__main__': unittest.main()
