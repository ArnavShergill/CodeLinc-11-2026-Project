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

    def test_http_accepts_chat_without_checkbox_and_rejects_invalid_requests(self):
        with patch('api_server.API_request',return_value='Hello'):
            self.assertEqual(self.request({'message':'hello'})[0],200)
        self.assertEqual(self.request({'message':'hello'},origin='https://evil.example')[0],403)
        self.assertEqual(self.request({'message':'x'*2001})[0],400)

    def test_http_passes_context_and_hides_provider_errors(self):
        body={'message':'hello','context':{'profile':{'annualIncome':90000}}}
        with patch('api_server.API_request',return_value='Answer') as model:
            self.assertEqual(self.request(body),(200,{'reply':'Answer'}))
            self.assertEqual(model.call_args.args[2]['profile'],{'annualIncome':90000})
        with patch('api_server.API_request',side_effect=RuntimeError('secret-provider-details')):
            status,payload=self.request(body)
            self.assertEqual(status,502)
            self.assertNotIn('secret-provider-details',str(payload))


class ConnectedFlowTests(unittest.TestCase):
    def profile(self):
        return dict(annualIncome=75000,spouseAnnualIncome=45000,numberOfDependents=3,childrenAges=[7,11],mortgageBalance=180000,otherDebt=25000,finalExpenses=15000,desiredAnnualIncome=50000,incomeReplacementYears=10,collegeFundingNeed=80000,existingLifeInsurance=100000,availableAssets=50000,inflationRate=.02,investmentReturnRate=.05)

    def test_existing_reference_calculator_is_used_and_inputs_change_the_result(self):
        from calculator_bridge import calculate
        profile=self.profile();base=calculate(profile)
        self.assertEqual(base['calculator'],'team-reference')
        self.assertEqual(base['additionalCoverageNeeded'],590375.55)
        changed=calculate({**profile,'mortgageBalance':250000})
        self.assertEqual(changed['additionalCoverageNeeded']-base['additionalCoverageNeeded'],70000)
        self.assertEqual(profile['mortgageBalance'],180000)
        self.assertEqual(calculate({**profile,'existingLifeInsurance':2000000})['additionalCoverageNeeded'],0)

    def test_projection_uses_same_plan_and_explicit_policy_expiry(self):
        from calculator_bridge import simulate
        projection=simulate(self.profile(),proposed_coverage=300000,policy_years=10)
        self.assertEqual(projection['timeline'][0]['additionalNeed'],590375.55)
        self.assertEqual(projection['timeline'][0]['remainingGap'],290375.55)
        self.assertEqual(projection['timeline'][2]['proposedCoverage'],0)
        self.assertEqual(projection['timeline'][2]['additionalNeed'],150000)
        self.assertTrue(any('remain unchanged' in item for item in projection['assumptions']))

    def test_scenarios_only_apply_selected_fields(self):
        from calculator_bridge import simulate
        projection=simulate(self.profile(),'home',{'mortgageBalance':250000})
        self.assertEqual(projection['result']['additionalCoverageNeeded'],660375.55)
        self.assertEqual(projection['baseResult']['additionalCoverageNeeded'],590375.55)
        with self.assertRaises(ValueError): simulate(self.profile(),'home',{'existingLifeInsurance':1000000})

    def test_lessons_are_generated_with_confirmed_context_and_validated(self):
        from learning import make_lesson
        lesson={'title':'Who life insurance helps','explanation':'A payable death benefit can support beneficiaries.','example':'Your dependents may use it for financial responsibilities.','question':'Who receives a payable death benefit?','choices':['Beneficiaries','The bank automatically','Everyone who starts a policy'],'correctIndex':0,'why':'Beneficiaries receive the payable benefit under policy terms.'}
        with patch('learning._chat',return_value=json.dumps(lesson)) as model:
            output=make_lesson('protection',{'profile':self.profile(),'resultSource':'backend'})
            self.assertEqual(output['correctIndex'],0)
            self.assertIn('75000',model.call_args.args[0][1]['content'])
        with patch('learning._chat',return_value='{"choices":[],"correctIndex":10}'):
            with self.assertRaises(RuntimeError): make_lesson('protection',{})

    def test_intake_can_teach_without_inventing_a_value(self):
        with patch('chat_features._chat',return_value='{"updates":{},"help":"Annual income means what you earn in a year before taxes. What amount would you like to record?"}'):
            result=capture_intake('What does annual income mean?',{},'annualIncome')
            self.assertEqual(result['updates'],{})
            self.assertIn('before taxes',result['reply'])

if __name__=='__main__': unittest.main()
