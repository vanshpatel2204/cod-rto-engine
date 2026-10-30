"""
Unit Tests for Oytra COD RTO Unit Economics
Validates the mathematical justification for the ₹30 prepaid discount and courier RTO costs.
"""

import unittest
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from decision_engine import load_config


class TestUnitEconomics(unittest.TestCase):

    def setUp(self):
        self.config = load_config()
        self.biz = self.config["business"]

    def test_rto_cost_per_order_formula(self):
        """
        RTO Cost = Forward Shipping (₹65) + Return Shipping (₹65) + Packaging (₹25)
                   + Damage Rate (8%) * Avg Product Cost (₹180) = ₹169.40.
        """
        fwd = self.biz["forward_shipping_cost"]
        rtn = self.biz["return_shipping_cost"]
        pkg = self.biz["packaging_handling_cost"]
        dmg = self.biz["damage_rate"] * self.biz["avg_product_cost"]
        total_rto_cost = fwd + rtn + pkg + dmg

        self.assertAlmostEqual(total_rto_cost, 169.40, places=1)

    def test_prepaid_discount_positive_net_margin(self):
        """
        Converting COD (28% RTO) to Prepaid (4% RTO) saves:
        (0.28 - 0.04) * ₹169.40 = ₹40.66 gross savings per order.
        Offering a ₹30 discount yields a net margin gain of ~₹10.66 per converted order.
        """
        rto_cost = 169.40
        cod_expected_loss = 0.28 * rto_cost
        prepaid_expected_loss = 0.04 * rto_cost
        gross_saving = cod_expected_loss - prepaid_expected_loss
        discount = self.config["prepaid_nudge"]["discount_amount_inr"]

        net_margin_gain = gross_saving - discount
        self.assertGreater(net_margin_gain, 0.0)
        self.assertAlmostEqual(gross_saving, 40.656, places=2)
        self.assertAlmostEqual(net_margin_gain, 10.656, places=2)


if __name__ == "__main__":
    unittest.main()
