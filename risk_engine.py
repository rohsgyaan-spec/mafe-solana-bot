from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class RiskConfig:
    min_liquidity: float = 10000
    min_volume_24h: float = 5000
    flag_pair_age_hours: float = 2
    max_volume_liquidity_ratio: float = 5

def assess_pair(pair: dict, config: RiskConfig) -> dict:
    flags = []
    liquidity = float(((pair.get('liquidity') or {}).get('usd')) or 0)
    volume = float(((pair.get('volume') or {}).get('h24')) or 0)
    ratio = volume / liquidity if liquidity > 0 else float('inf')
    age_hours = None
    created = pair.get('pairCreatedAt')
    if created:
        try:
            age_hours = max(0.0, (datetime.now(timezone.utc).timestamp() - float(created)/1000) / 3600)
        except (TypeError, ValueError):
            pass
    if liquidity < config.min_liquidity: flags.append(f'Low liquidity (${liquidity:,.0f} < ${config.min_liquidity:,.0f})')
    if volume < config.min_volume_24h: flags.append(f'Low 24h volume (${volume:,.0f} < ${config.min_volume_24h:,.0f})')
    if age_hours is not None and age_hours < config.flag_pair_age_hours: flags.append(f'New pair ({age_hours:.1f}h old)')
    if ratio > config.max_volume_liquidity_ratio: flags.append(f'High volume/liquidity ratio ({ratio:.1f}x)')
    if not pair.get('baseToken', {}).get('address'): flags.append('Missing token address')
    level = 'LOW' if not flags else ('HIGH' if liquidity < config.min_liquidity/2 or (age_hours is not None and age_hours < 0.5) else 'MEDIUM')
    return {'level': level, 'flags': flags, 'pair_age_hours': round(age_hours, 2) if age_hours is not None else None, 'volume_liquidity_ratio': ratio}
