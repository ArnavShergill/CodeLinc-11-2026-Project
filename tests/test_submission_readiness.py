"""Startup retries must tolerate Docker port publication before server readiness."""
from http.client import RemoteDisconnected
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError
from scripts.smoke_submission import wait_for_health


class SubmissionReadinessTests(unittest.TestCase):
    def test_connection_reset_and_closed_socket_retry_then_pass(self):
        probe = Mock(side_effect=[ConnectionResetError('Starting'), RemoteDisconnected('Starting'),
                                  URLError('Connection refused'), {'status': 'ok'}])
        with patch('scripts.smoke_submission.time.sleep') as sleep:
            wait_for_health(probe)
        self.assertEqual(probe.call_count, 4)
        self.assertEqual(sleep.call_count, 3)

    def test_persistent_failure_does_not_pass(self):
        probe = Mock(side_effect=ConnectionResetError('Unavailable'))
        with patch('scripts.smoke_submission.time.sleep') as sleep:
            with self.assertRaises(ConnectionResetError):
                wait_for_health(probe, attempts=3)
        self.assertEqual(probe.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_unhealthy_response_is_not_accepted(self):
        with self.assertRaises(AssertionError):
            wait_for_health(lambda: {'status': 'failed'})


class OfflineIntakeRegressionTests(unittest.TestCase):
    def test_direct_answers_do_not_call_provider(self):
        from chat_features import capture_intake
        from unittest.mock import patch
        cases = [('annualIncome','about 100k',100000), ('otherDebt','none',0),
                 ('incomeReplacementYears','ten years',10), ('childrenAges','7, 11',[7,11])]
        with patch('chat_features._chat', side_effect=AssertionError('No provider needed')) as provider:
            for field, answer, expected in cases:
                self.assertEqual(capture_intake(answer, {}, field)['updates'], {field:expected})
            provider.assert_not_called()

    def test_offline_lesson_is_labelled_and_contextual(self):
        from learning import make_lesson
        from unittest.mock import patch
        with patch('learning._chat', side_effect=RuntimeError('offline')):
            lesson = make_lesson('types', {'profile':{'numberOfDependents':2}})
        self.assertEqual(lesson['mode'], 'offline')
        self.assertIn('unavailable', lesson['explanation'])
        self.assertIn('depend', lesson['example'])

    def test_unverified_lesson_amount_is_not_displayed(self):
        from learning import make_lesson
        from unittest.mock import patch
        import json
        data = {'title':'Lesson','explanation':'You need $999999 of coverage.', 'example':'Example',
                'question':'Question','choices':['A','B','C'],'correctIndex':0,'why':'Explanation'}
        with patch('learning._chat', return_value=json.dumps(data)):
            lesson = make_lesson('needs', {})
        self.assertNotIn('999999', json.dumps(lesson))
