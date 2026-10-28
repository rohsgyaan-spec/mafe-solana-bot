"""Safety gates for a future Solana execution adapter.

This module does NOT sign or send transactions. It validates trade intents and
keeps live execution disabled unless several explicit gates are satisfied.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class ExecutionConfig:
    live_trading_enabled: bool = False
    live_confirmation: str = ""
    max_order_usd: Decimal = Decimal("10")
    max_daily_loss_usd: Decimal = Decimal("10")
    max_open_positions: int = 1
    max_slippage_bps: int = 100
    max_priority_fee_lamports: int = 100_000
    require_simulation: bool = True

@dataclass(frozen=True)
class TradeIntent:
    mint: str
    side: str
    notional_usd: Decimal
    slippage_bps: int
    estimated_price_impact_pct: Decimal
    daily_realized_pnl_usd: Decimal
    open_positions: int
    simulation_passed: bool
    token_checks_passed: bool

@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reasons: tuple[str, ...]

ARM_PHRASE = "I UNDERSTAND LIVE SOLANA TRADING RISKS"


def validate_trade(intent: TradeIntent, config: ExecutionConfig) -> GuardResult:
    reasons = []
    if not config.live_trading_enabled:
        reasons.append("Live trading is disabled in configuration")
    if config.live_confirmation != ARM_PHRASE:
        reasons.append("Exact live confirmation phrase is missing")
    if not intent.mint or len(intent.mint) < 32 or len(intent.mint) > 50:
        reasons.append("Token mint address format is invalid")
    if intent.side.upper() not in {"BUY", "SELL"}:
        reasons.append("Side must be BUY or SELL")
    if intent.notional_usd <= 0:
        reasons.append("Order notional must be positive")
    if intent.notional_usd > config.max_order_usd:
        reasons.append(f"Order exceeds max order size (${config.max_order_usd})")
    if intent.daily_realized_pnl_usd <= -config.max_daily_loss_usd:
        reasons.append("Daily loss limit reached; trading kill switch engaged")
    if intent.open_positions >= config.max_open_positions and intent.side.upper() == "BUY":
        reasons.append("Maximum open-position limit reached")
    if intent.slippage_bps < 0 or intent.slippage_bps > config.max_slippage_bps:
        reasons.append("Slippage exceeds configured limit")
    if intent.estimated_price_impact_pct < 0 or intent.estimated_price_impact_pct > Decimal("3"):
        reasons.append("Estimated price impact is invalid or above 3% hard cap")
    if not intent.token_checks_passed:
        reasons.append("Token safety checks did not pass")
    if config.require_simulation and not intent.simulation_passed:
        reasons.append("Transaction simulation did not pass")
    return GuardResult(allowed=not reasons, reasons=tuple(reasons))


def assert_live_execution_allowed(intent: TradeIntent, config: ExecutionConfig) -> None:
    """Fail closed: raise instead of executing when any guard fails."""
    result = validate_trade(intent, config)
    if not result.allowed:
        raise PermissionError("Trade blocked: " + "; ".join(result.reasons))
    # Intentionally no transaction execution here. A separately reviewed signer
    # and swap adapter must be implemented before any live trading is possible.
    raise NotImplementedError("Safety checks passed, but no live transaction adapter is installed.")
