# Mafe Solana Bot — Windows 11 starter v2

This package contains a local Streamlit dashboard for Solana pair scanning and paper trading, plus a fail-closed execution safety gate for future development.

## Install (beginner-friendly)
1. Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/.
2. During setup, check **Add python.exe to PATH**.
3. Extract this ZIP to a simple folder such as `C:\MafeSolanaBot`.
4. Open that folder in File Explorer, click the address bar, type `cmd`, and press Enter.
5. Run these commands one at a time:

```bat
py --version
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m unittest discover -s tests -v
streamlit run app.py
```

6. Keep the Command Prompt open while using the app. If the browser does not open automatically, visit `http://localhost:8501`.
7. Stop the app with `Ctrl+C` in Command Prompt.

## What's in v2
- Existing market scanner and paper-trading dashboard (`app.py`).
- Heuristic pair risk flags (`risk_engine.py`).
- Fail-closed order-intent safety checks (`execution_guard.py`): live disabled by default, explicit confirmation phrase, max order, daily-loss kill switch, open-position cap, slippage and price-impact limits, token-check and simulation requirements.
- Unit tests for key block conditions (`tests/`).

## Critical scope boundary
This is **not yet an automatic live-trading bot**. The guard does not sign, submit, or settle a Solana transaction. `assert_live_execution_allowed()` intentionally raises `NotImplementedError` even when checks pass. A separately reviewed transaction adapter is required before any live trades can happen.

## Recommended next development stages
1. Add tests and paper-trading forward validation.
2. Add token mint/authority checks and external risk-source adapters, treating them as signals rather than guarantees.
3. Add swap quote + transaction simulation (without signing).
4. Add a separate signer service with a dedicated low-balance wallet, never expose the seed phrase in Streamlit, logs, screenshots, or source control.
5. Add idempotent transaction submission, confirmation polling, reconciliation against actual wallet balances, audit logs, and emergency stop.
6. Only after review, enable small-size live trading with a hard daily-loss limit. Meme coins can lose all liquidity or value; no safety check guarantees profit or prevents every rug pull.

## Security
- Never share your seed phrase or private key with anyone or paste it into ChatGPT.
- Do not commit `.env` or wallet secrets to Git.
- Use a dedicated wallet, not your main holdings wallet.
- Start with paper trading; there is no profit guarantee.
