"""Regression checks for the bounded PTY diagnostic client."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_pty


class RequestCounterTest(unittest.TestCase):
    def setUp(self):
        self.previous_counter = test_pty.packet_counter
        test_pty.packet_counter = 7

    def tearDown(self):
        test_pty.packet_counter = self.previous_counter

    def test_next_request_follows_terminal_ack_without_skipping(self):
        frames = [
            {"counter": 9, "frame_id": 0xFC, "data": [2, 4, 0x1E]},
            {"counter": 11, "frame_id": 0x09, "data": []},
            {"counter": 13, "frame_id": 0xFE, "data": [0x51]},
            {"counter": 15, "frame_id": 0x09, "data": []},
        ]
        sent = []

        def record_send(_ser, frame_id, data=None, counter=None):
            sent.append((frame_id, counter))
            return True

        with patch.object(test_pty, "send_ecu_packet", side_effect=record_send), \
             patch.object(test_pty, "read_ecu_packet", side_effect=frames), \
             patch.object(test_pty, "process_incoming_packet"):
            self.assertEqual(len(test_pty.request_data(None, 0x07)), 2)
            self.assertEqual(len(test_pty.request_data(None, 0x01, [1, 0, 0x63])), 2)

        self.assertEqual(sent, [(0x07, 8), (0x09, 10),
                                (0x01, 12), (0x09, 14)])
        self.assertEqual(test_pty.packet_counter, 15)

    def test_timeout_before_terminal_ack_is_failure(self):
        with patch.object(test_pty, "send_ecu_packet", return_value=True), \
             patch.object(test_pty, "read_ecu_packet", return_value=None):
            self.assertIsNone(test_pty.request_data(None, 0x07))

    def test_memory_reader_preserves_nonzero_selector(self):
        with patch.object(test_pty, "request_data", return_value=[]) as request:
            test_pty.read_memory_byte(None, 0xF8, 0x0C)
        request.assert_called_once_with(None, frame_id=0x01,
                                        data=[0x01, 0xF8, 0x0C])


if __name__ == "__main__":
    unittest.main()
