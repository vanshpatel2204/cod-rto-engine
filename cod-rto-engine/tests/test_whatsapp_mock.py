"""
Unit Tests for WhatsApp Confirmation & Conversational Mock
Run: python -m unittest discover tests
"""

import unittest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from whatsapp_mock import (
    simulate_confirmation_flow,
    simulate_prepaid_nudge_flow,
    simulate_custom_ai_flow,
    generate_ai_chat_response,
    ReplyType
)


class TestWhatsAppMock(unittest.TestCase):

    def test_confirmation_flow_yes(self):
        """Customer replying YES should result in 'ship' action."""
        res = simulate_confirmation_flow("ORD-101", 649.0, "Hair Mask", ReplyType.YES)
        self.assertEqual(res.final_action, "ship")
        self.assertFalse(res.converted)
        self.assertEqual(len(res.messages), 3)

    def test_confirmation_flow_no(self):
        """Customer replying NO should result in 'cancel' action with saved freight."""
        res = simulate_confirmation_flow("ORD-102", 649.0, "Hair Mask", ReplyType.NO)
        self.assertEqual(res.final_action, "cancel")
        self.assertEqual(len(res.messages), 4)

    def test_confirmation_flow_timeout(self):
        """No reply within 24h should apply default hold_cancel policy."""
        res = simulate_confirmation_flow("ORD-103", 649.0, "Hair Mask", ReplyType.NO_REPLY, no_reply_action="hold_cancel")
        self.assertEqual(res.final_action, "hold_cancel")

    def test_prepaid_nudge_flow_yes(self):
        """Customer accepting prepaid discount should result in 'converted_to_prepaid'."""
        res = simulate_prepaid_nudge_flow("ORD-201", 899.0, "Serum", 30, "PAYNOW201", ReplyType.YES)
        self.assertEqual(res.final_action, "converted_to_prepaid")
        self.assertTrue(res.converted)
        self.assertGreater(res.revenue_impact_inr, 0.0)

    def test_conversational_ai_return_policy(self):
        """Query about return policy should return 7-day doorstep replacement info."""
        reply, intent, ops_action, meta = generate_ai_chat_response(
            "ORD-8291", 649.0, "Anti-Dandruff Mask", "Confirmation", "does this have return policy?"
        )
        self.assertEqual(intent, "inquiry")
        self.assertIn("7-day", reply)

    def test_conversational_ai_delivery_timing(self):
        """Query about 5 PM delivery slot should note courier instructions."""
        reply, intent, ops_action, meta = generate_ai_chat_response(
            "ORD-8291", 649.0, "Anti-Dandruff Mask", "Confirmation", "Bhaiya 5 baje ke baad deliver ho sakta hai kya?", language="hinglish"
        )
        self.assertEqual(intent, "inquiry")
        self.assertTrue("courier" in reply.lower() or "delivery" in reply.lower())

    def test_conversational_ai_cancellation(self):
        """Cancellation request in custom AI chat should trigger cancel intent."""
        reply, intent, ops_action, meta = generate_ai_chat_response(
            "ORD-8291", 649.0, "Anti-Dandruff Mask", "Confirmation", "cancel my order please"
        )
        self.assertEqual(intent, "cancel")
        self.assertIn("cancelled", reply.lower())


if __name__ == "__main__":
    unittest.main()
