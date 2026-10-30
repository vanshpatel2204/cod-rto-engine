"""
Unit Tests for Oytra COD RTO Decision Engine
Run: python -m unittest discover -s tests -p "test_*.py"
"""

import unittest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from decision_engine import OrderInput, decide, load_config, Action


class TestDecisionEngine(unittest.TestCase):

    def setUp(self):
        self.config = load_config()

    def test_low_risk_repeat_customer_ships_as_is(self):
        """VIP repeat buyer with clean address should be classified as SHIP_AS_IS (score <= 0.25)."""
        order = OrderInput(
            order_id="TEST-001",
            customer_name="Pooja Sharma",
            address="Flat 402, Sea Green Apartments, Linking Road, Bandra West",
            pincode="400050",
            city="Mumbai",
            state="Maharashtra",
            order_value=649.0,
            is_first_order=False,
            customer_total_orders=4,
            customer_previous_rto_count=0,
            pincode_historical_rto_rate=0.08,
            num_items=1
        )
        res = decide(order, self.config, use_llm=False)
        self.assertEqual(res.action, Action.SHIP_AS_IS)
        self.assertLessEqual(res.risk_score, self.config["risk_thresholds"]["ship_as_is_max"])

    def test_moderate_risk_nudged_to_prepaid(self):
        """New customer with moderate pincode risk falls into NUDGE_TO_PREPAID bucket (0.25 < score <= 0.50)."""
        order = OrderInput(
            order_id="TEST-002",
            customer_name="Rahul Verma",
            address="House 12, 4th Cross, Indiranagar",
            pincode="560038",
            city="Bengaluru",
            state="Karnataka",
            order_value=649.0,
            is_first_order=True,
            customer_total_orders=1,
            customer_previous_rto_count=0,
            pincode_historical_rto_rate=0.35,
            num_items=2
        )
        res = decide(order, self.config, use_llm=False)
        self.assertEqual(res.action, Action.NUDGE_TO_PREPAID)
        self.assertGreater(res.risk_score, self.config["risk_thresholds"]["ship_as_is_max"])
        self.assertLessEqual(res.risk_score, self.config["risk_thresholds"]["nudge_to_prepaid_max"])

    def test_high_pincode_risk_triggers_confirmation(self):
        """Incomplete address + high RTO pincode triggers SHIP_AFTER_CONFIRMATION (0.50 < score <= 0.72)."""
        order = OrderInput(
            order_id="TEST-003",
            customer_name="Mohd Imran",
            address="Near Station",
            pincode="243003",
            city="Bareilly",
            state="Uttar Pradesh",
            order_value=649.0,
            is_first_order=True,
            customer_total_orders=1,
            customer_previous_rto_count=0,
            pincode_historical_rto_rate=0.55,
            num_items=3
        )
        res = decide(order, self.config, use_llm=False)
        self.assertEqual(res.action, Action.SHIP_AFTER_CONFIRMATION)
        self.assertGreater(res.risk_score, self.config["risk_thresholds"]["nudge_to_prepaid_max"])
        self.assertLessEqual(res.risk_score, self.config["risk_thresholds"]["confirm_before_ship_max"])

    def test_fake_name_and_gibberish_address_triggers_hold(self):
        """Obvious keyboard mash name ('asdf') and incomplete address must trigger HOLD_CANCEL (score > 0.72)."""
        order = OrderInput(
            order_id="TEST-004",
            customer_name="asdf",
            address="near station na",
            pincode="800001",
            city="Patna",
            state="Bihar",
            order_value=2499.0,
            is_first_order=True,
            customer_total_orders=1,
            customer_previous_rto_count=2,
            pincode_historical_rto_rate=0.55,
            num_items=4
        )
        res = decide(order, self.config, use_llm=False)
        self.assertEqual(res.action, Action.HOLD_CANCEL)
        self.assertGreater(res.risk_score, self.config["risk_thresholds"]["confirm_before_ship_max"])

    def test_risk_score_is_bounded_between_zero_and_one(self):
        """Risk score must strictly stay within [0.0, 1.0]."""
        order = OrderInput(
            order_id="TEST-BOUNDS",
            customer_name="Test Buyer",
            address="Main Road, Sector 15",
            pincode="110001",
            city="Delhi",
            state="Delhi",
            order_value=649.0
        )
        res = decide(order, self.config, use_llm=False)
        self.assertGreaterEqual(res.risk_score, 0.0)
        self.assertLessEqual(res.risk_score, 1.0)


if __name__ == "__main__":
    unittest.main()
