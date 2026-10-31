"""Human percentage points normalize once before deterministic calculation."""
import unittest
import io
import json
from unittest.mock import patch
import AI_interact as ai
from chat_features import capture_intake, clean_context
from api_server import LifeMapAPIHandler, _requests


class PercentageInputTests(unittest.TestCase):
    def test_http_rate_answers_and_blank_errors(self):
        for path in ('/api/intake', '/api/chat'):
            for answer in ('2.5', '0.02', ''):
                with self.subTest(path=path, answer=answer):
                    _requests.clear()
                    body = {'message': answer, 'field': 'inflationRate',
                            'context': {'profile': {}, 'assessment': {'active': True, 'field': 'inflationRate'}}}
                    raw = json.dumps(body).encode()
                    handler = object.__new__(LifeMapAPIHandler)
                    handler.path = path; handler.headers = {'Content-Length': str(len(raw))}
                    handler.client_address = ('percentage-test', 1); handler.rfile = io.BytesIO(raw)
                    output = []; handler._send_json = lambda status, payload: output.append((status, payload))
                    with patch.object(ai, '_chat', return_value='{}'):
                        handler.do_POST()
                    status, result = output[0]
                    if answer == '':
                        self.assertEqual(status, 400)
                        self.assertIn('such as 2 or 2%', result['error'])
                    elif answer == '0.02':
                        self.assertEqual(status, 200)
                        self.assertIn('0.02% or 2%', result['reply'])
                    else:
                        self.assertEqual(status, 200)
                        self.assertEqual(result['updates' if path == '/api/intake' else 'profile']['inflationRate'], .025)
        _requests.clear()

    def test_both_rates_valid_inputs_in_intake_and_chat(self):
        cases = [('2', .02), ('2%', .02), ('2.5', .025), ('2.5%', .025),
                 ('5', .05), ('5%', .05), ('0', 0), ('about 2 percent', .02),
                 ('0.02%', .0002), ('about two percent', .02)]
        for field in ai.RATE_FIELDS:
            for answer, expected in cases:
                with self.subTest(field=field, answer=answer), patch.object(ai, '_chat', return_value='{}'):
                    intake = capture_intake(answer, {}, field)
                    self.assertEqual(intake['updates'], {field: expected})
                    profile = ai.get_demo_profile()
                    context = clean_context({'profile': profile, 'assessment': {'active': True, 'field': field}})
                    with patch('calculator_bridge.calculate', wraps=__import__('calculator_bridge').calculate) as calculator:
                        chat = ai.chat_turn(answer, context=context)
                    self.assertEqual(chat['profile'][field], expected)
                    calculator.assert_called_once_with(chat['profile'])
                    self.assertEqual(profile, ai.get_demo_profile())

    def test_invalid_and_ambiguous_answers_preserve_profile_and_do_not_calculate(self):
        for field in ai.RATE_FIELDS:
            for answer in ('', ' ', '0.02', '-2', '-2%', '89', '89%', 'banana'):
                with self.subTest(field=field, answer=answer), patch('calculator_bridge.calculate') as calculate:
                    intake = capture_intake(answer, ai.get_demo_profile(), field)
                    chat = ai.chat_turn(answer, context={'profile': ai.get_demo_profile(),
                                                        'assessment': {'active': True, 'field': field}})
                    self.assertEqual(intake['updates'], {})
                    self.assertEqual(chat['profile'], ai.get_demo_profile())
                    self.assertEqual(chat['assessment']['field'], field)
                    self.assertEqual(chat['reply'], intake['reply'])
                    self.assertIn('0.02% or 2%' if answer == '0.02' else 'such as 2 or 2%', chat['reply'])
                    calculate.assert_not_called()

    def test_labelled_rates_override_incorrect_model_units_in_both_paths(self):
        message = 'My inflation is 2.5 and investment return is 5%'
        with patch.object(ai, '_chat', return_value='{"inflationRate":2.5,"investmentReturnRate":5}'):
            profile = ai.extract_profile_data(message, {'mortgageBalance': 100000})
        self.assertEqual(profile['inflationRate'], .025)
        self.assertEqual(profile['investmentReturnRate'], .05)
        self.assertEqual(profile['mortgageBalance'], 100000)
        with patch('chat_features._chat', return_value='{"updates":{"inflationRate":2.5,"investmentReturnRate":5}}'):
            updates = capture_intake(message, {}, None)['updates']
        self.assertEqual(updates, {'inflationRate': .025, 'investmentReturnRate': .05})

    def test_labelled_fraction_requires_clarification_before_model_call(self):
        with patch.object(ai, '_chat') as model:
            with self.assertRaisesRegex(ai.RateInputError, '0.02% or 2%'):
                ai.extract_profile_data('My inflation rate is 0.02', {})
            model.assert_not_called()

    def test_unstated_rates_cannot_be_invented_by_model(self):
        with patch.object(ai, '_chat', return_value='{"mortgageBalance":100000,"inflationRate":0.5}'):
            profile = ai.extract_profile_data('My mortgage is 100k', {})
        self.assertNotIn('inflationRate', profile)
