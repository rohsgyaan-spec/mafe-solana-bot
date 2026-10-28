import unittest
from decimal import Decimal
from execution_guard import ExecutionConfig, TradeIntent, validate_trade, ARM_PHRASE

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.intent = TradeIntent(
            mint="So11111111111111111111111111111111111111112",
            side="BUY", notional_usd=Decimal("5"), slippage_bps=50,
            estimated_price_impact_pct=Decimal("0.5"),
            daily_realized_pnl_usd=Decimal("0"), open_positions=0,
            simulation_passed=True, token_checks_passed=True,
        )

    def test_live_disabled_fails_closed(self):
        result = validate_trade(self.intent, ExecutionConfig())
        self.assertFalse(result.allowed)
        self.assertTrue(any("disabled" in reason.lower() for reason in result.reasons))

    def test_order_over_limit_blocked(self):
        cfg = ExecutionConfig(live_trading_enabled=True, live_confirmation=ARM_PHRASE,
                              max_order_usd=Decimal("2"))
        result = validate_trade(self.intent, cfg)
        self.assertFalse(result.allowed)
        self.assertTrue(any("max order" in reason.lower() for reason in result.reasons))

    def test_daily_loss_kill_switch(self):
        cfg = ExecutionConfig(live_trading_enabled=True, live_confirmation=ARM_PHRASE,
                              max_daily_loss_usd=Decimal("10"))
        intent = TradeIntent(**{**self.intent.__dict__, "daily_realized_pnl_usd": Decimal("-10")})
        result = validate_trade(intent, cfg)
        self.assertFalse(result.allowed)
        self.assertTrue(any("daily loss" in reason.lower() for reason in result.reasons))

if __name__ == "__main__":
    unittest.main()
