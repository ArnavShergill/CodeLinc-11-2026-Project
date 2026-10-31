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
