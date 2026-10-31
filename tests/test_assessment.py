"""Assessment orchestration tests: mock extraction, exercise the real calculator."""
import io
import json
import unittest
from unittest.mock import patch
import AI_interact as ai
from api_server import LifeMapAPIHandler, _requests


class AssessmentTests(unittest.TestCase):
    def context(self, profile=None):
        return {'profile': profile or {}, 'assessment': {'active': True}}

    def turn(self, message, profile=None, extraction='{}'):
        with patch.object(ai, '_chat', return_value=extraction):
            return ai.chat_turn(message, context=self.context(profile))

    def test_multiple_values_retained_and_known_fields_skipped(self):
        original={'existingLifeInsurance':100000,'childrenAges':[7,11]}
        result=self.turn('Mortgage 180k, other debt 25k, final expenses 15k', original,
            '{"mortgageBalance":180000,"otherDebt":25000,"finalExpenses":15000,"childrenAges":null}')
        self.assertEqual(result['profile']['existingLifeInsurance'],100000)
        self.assertEqual(result['profile']['childrenAges'],[7,11])
        self.assertEqual(result['reply'],ai._MISSING_FIELD_QUESTIONS['desiredAnnualIncome'])
        self.assertEqual(result['reply'].count('?'),1)
        self.assertEqual(original,{'existingLifeInsurance':100000,'childrenAges':[7,11]})

    def test_extraction_receives_current_question_and_collects_all_fields(self):
        with patch.object(ai,'_chat',return_value='```json\n{"mortgageBalance":200000,"otherDebt":0}\n```') as model:
            result=ai.extract_profile_data('I owe 200k on my home and no other debt',{})
        self.assertEqual(result['mortgageBalance'],200000)
        self.assertEqual(result['otherDebt'],0)
        self.assertIn(ai._MISSING_FIELD_QUESTIONS['mortgageBalance'],model.call_args.args[0][1]['content'])

    def test_none_zero_and_approximate_amount(self):
        for answer,expected in [('none',0),('zero',0),('0',0),('about 100k',100000),('$180,000',180000)]:
            with self.subTest(answer=answer):
                result=self.turn(answer)
                self.assertEqual(result['profile']['mortgageBalance'],expected)
                self.assertEqual(result['reply'],ai._MISSING_FIELD_QUESTIONS['otherDebt'])

    def test_word_years_in_context(self):
        profile={'mortgageBalance':0,'otherDebt':0,'finalExpenses':15000,'desiredAnnualIncome':50000}
        result=self.turn('ten years',profile)
        self.assertEqual(result['profile']['incomeReplacementYears'],10)
        self.assertEqual(result['reply'],ai._MISSING_FIELD_QUESTIONS['collegeFundingNeed'])

    def test_labelled_answer_does_not_populate_wrong_field(self):
        result=self.turn('I already have 100k life insurance',extraction='{"existingLifeInsurance":100000}')
        self.assertNotIn('mortgageBalance',result['profile'])
        self.assertEqual(result['reply'],ai._MISSING_FIELD_QUESTIONS['mortgageBalance'])

    def test_omitted_null_fields_do_not_delete_values_and_corrections_replace(self):
        result=self.turn('Actually mortgage is 90k',{'mortgageBalance':180000,'otherDebt':0},
            '{"mortgageBalance":90000,"otherDebt":null}')
        self.assertEqual(result['profile']['mortgageBalance'],90000)
        self.assertEqual(result['profile']['otherDebt'],0)

    def test_completion_calls_existing_calculator_with_valid_profile(self):
        from calculator_bridge import calculate
        profile=ai.get_demo_profile();profile.pop('availableAssets')
        with patch.object(ai,'_chat',return_value='{}'),patch('calculator_bridge.calculate',wraps=calculate) as calculator:
            result=ai.chat_turn('50k',context=self.context(profile))
        calculator.assert_called_once_with(result['profile'])
        self.assertEqual(result['mode'],'complete')
        self.assertEqual(result['missingFields'],[])
        self.assertEqual(result['result']['additionalCoverageNeeded'],590375.55)
        self.assertNotIn('?',result['reply'])
        self.assertIn('590375.55',result['reply'])

    def test_complete_profile_does_not_ask_more_questions(self):
        result=self.turn('Calculate my insurance needs',ai.get_demo_profile())
        self.assertEqual(result['mode'],'complete')
        self.assertIsNone(ai.get_next_question(result['profile']))

    def test_model_cannot_invent_coverage_amount(self):
        with patch.object(ai,'_chat',return_value='You need $99999999 in insurance.'):
            explanation=ai.explain_result({'additionalCoverageNeeded':125000})
        self.assertIn('125000',explanation)
        self.assertNotIn('99999999',explanation)

    def test_educational_interruption_preserves_assessment(self):
        context=self.context({'mortgageBalance':100000})
        with patch.object(ai,'_educational_reply',return_value='Term life covers a set period.'),patch.object(ai,'extract_profile_data') as extract:
            result=ai.chat_turn('What is term life insurance?',context=context)
        extract.assert_not_called()
        self.assertEqual(result['profile'],context['profile'])
        self.assertTrue(result['assessment']['active'])
        self.assertEqual(result['mode'],'education')
        resumed=self.turn('none',result['profile'])
        self.assertEqual(resumed['profile']['otherDebt'],0)

    def test_assessment_intent_starts_one_question(self):
        with patch.object(ai,'_chat',return_value='{}'),patch.object(ai,'_educational_reply') as educator:
            result=ai.chat_turn('How much insurance do I need?',context={'profile':{}})
        educator.assert_not_called()
        self.assertEqual(result['reply'],ai._MISSING_FIELD_QUESTIONS['mortgageBalance'])
        self.assertTrue(result['assessment']['active'])

    def test_invalid_values_and_unrelated_numbers_cannot_be_committed(self):
        for extracted in ['{"mortgageBalance":-100}','{"mortgageBalance":true}','{"mortgageBalance":NaN}']:
            with patch.object(ai,'_chat',return_value=extracted):
                with self.assertRaises(ValueError):ai.extract_profile_data('my mortgage',{})
        with patch.object(ai,'_educational_reply',return_value='Term coverage lasts a set period.'):
            result=self.turn('What does 20-year term mean?')
        self.assertNotIn('mortgageBalance',result['profile'])

    def test_direct_answer_survives_provider_outage(self):
        with patch.object(ai,'_chat',side_effect=RuntimeError('offline')):
            result=ai.chat_turn('about 100k',context=self.context())
        self.assertEqual(result['profile']['mortgageBalance'],100000)

    def test_existing_calculator_explanation_cannot_invent_an_amount(self):
        with patch.object(ai,'_chat',return_value='Buy a million dollars of coverage.'):
            result=ai.chat_turn('Explain the provided calculator result',context={'profile':{},'result':{'additionalCoverageNeeded':125000}})
        self.assertIn('125000',result['reply'])
        self.assertNotIn('million',result['reply'])

    def test_legacy_partial_profile_context_continues_assessment(self):
        with patch.object(ai, '_chat', return_value='{}'):
            result=ai.chat_turn('none',context={'profile':{'mortgageBalance':100000}})
        self.assertEqual(result['profile']['otherDebt'],0)
        self.assertEqual(result['reply'],ai._MISSING_FIELD_QUESTIONS['finalExpenses'])

    def test_education_is_concise_plain_text(self):
        with patch.object(ai,'_educational_reply',return_value='**Term life** covers a set period. It can protect your family. Coverage ends at the end of that period. Extra sentence.'):
            result=ai.chat_turn('What is term life insurance?')
        self.assertNotIn('**',result['reply'])
        self.assertNotIn('Extra sentence',result['reply'])
        self.assertFalse(result['assessment']['active'])

    def test_http_round_trip_carries_profile_without_global_session(self):
        _requests.clear()
        def request(body):
            raw=json.dumps(body).encode();handler=object.__new__(LifeMapAPIHandler)
            handler.path='/api/chat';handler.headers={'Content-Length':str(len(raw))}
            handler.client_address=('assessment-test',1);handler.rfile=io.BytesIO(raw)
            output=[];handler._send_json=lambda status,payload:output.append((status,payload))
            handler.do_POST();return output[0]
        with patch.object(ai,'_chat',return_value='{}'):
            status,first=request({'message':'How much insurance do I need?'})
            status,second=request({'message':'100k','context':{'profile':first['profile'],'assessment':first['assessment']}})
            status,third=request({'message':'none','context':{'profile':second['profile'],'assessment':second['assessment']}})
        self.assertEqual(status,200)
        self.assertEqual(third['profile']['mortgageBalance'],100000)
        self.assertEqual(third['profile']['otherDebt'],0)
        self.assertEqual(third['reply'],ai._MISSING_FIELD_QUESTIONS['finalExpenses'])
        _requests.clear()

if __name__=='__main__':unittest.main()
