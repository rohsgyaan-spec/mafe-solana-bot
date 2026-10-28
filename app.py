import os, json, time
from datetime import datetime, timezone
from pathlib import Path
import requests
import pandas as pd
import streamlit as st
from risk_engine import assess_pair, RiskConfig

APP_DIR = Path(__file__).parent
STATE_FILE = APP_DIR / 'paper_state.json'
DEX_SEARCH = 'https://api.dexscreener.com/latest/dex/search'
DEX_TOKEN = 'https://api.dexscreener.com/latest/dex/tokens/'

st.set_page_config(page_title='Mafe Solana Bot', page_icon='🟢', layout='wide')
st.markdown('''<style>
.block-container {padding-top: 1.2rem;}
[data-testid="stMetric"] {background:#101820;padding:14px;border:1px solid #263642;border-radius:12px;}
.stApp {background:#080d12;}
</style>''', unsafe_allow_html=True)

if 'paper' not in st.session_state:
    if STATE_FILE.exists():
        try: st.session_state.paper = json.loads(STATE_FILE.read_text())
        except Exception: st.session_state.paper = {'starting_balance':100.0,'cash':100.0,'trades':[]}
    else: st.session_state.paper = {'starting_balance':100.0,'cash':100.0,'trades':[]}

state = st.session_state.paper

def save_state():
    STATE_FILE.write_text(json.dumps(state, indent=2))

def num(x, default=0.0):
    try: return float(x or 0)
    except (TypeError, ValueError): return default

def fetch_search(query):
    try:
        r = requests.get(DEX_SEARCH, params={'q': query}, timeout=12)
        r.raise_for_status()
        pairs = r.json().get('pairs') or []
        return [p for p in pairs if p.get('chainId') == 'solana']
    except Exception as e:
        st.error(f'Coin data fetch failed: {e}')
        return []

def fetch_token(address):
    try:
        r = requests.get(DEX_TOKEN + address.strip(), timeout=12)
        r.raise_for_status()
        pairs = r.json().get('pairs') or []
        return [p for p in pairs if p.get('chainId') == 'solana']
    except Exception as e:
        st.error(f'Token lookup failed: {e}')
        return []

st.title('🟢 Mafe Solana Bot')
st.caption('Solana meme-coin scanner • risk checks • paper execution • trade log')
st.warning('SAFE MODE: Paper trading only. Live wallet signing and real order execution are intentionally disabled in this starter build.')

trades = state.get('trades', [])
realized = sum(num(t.get('pnl')) for t in trades if t.get('status') == 'CLOSED')
open_value = sum(num(t.get('size_usd')) for t in trades if t.get('status') == 'OPEN')
open_pnl = sum(num(t.get('pnl')) for t in trades if t.get('status') == 'OPEN')
initial = num(state.get('starting_balance'),100)
cash = num(state.get('cash'),initial)
equity = cash + open_value + open_pnl
wins = sum(1 for t in trades if t.get('status') == 'CLOSED' and num(t.get('pnl')) > 0)
losses = sum(1 for t in trades if t.get('status') == 'CLOSED' and num(t.get('pnl')) <= 0)

m1,m2,m3,m4,m5 = st.columns(5)
m1.metric('Paper equity', f'${equity:,.2f}', f'{equity-initial:+.2f} USD')
m2.metric('Cash', f'${cash:,.2f}')
m3.metric('Realized P&L', f'${realized:+,.2f}')
m4.metric('Closed trades', str(wins+losses))
m5.metric('Wins / Losses', f'{wins} / {losses}')

with st.sidebar:
    st.header('⚙️ Configuration')
    starting = st.number_input('Starting paper balance ($)', min_value=10.0, max_value=100000.0, value=float(initial), step=10.0)
    max_trade_pct = st.slider('Max trade size (% of equity)', 1, 25, 5)
    max_open = st.slider('Max open paper positions', 1, 10, 3)
    min_liq = st.number_input('Minimum liquidity ($)', min_value=0, value=10000, step=1000)
    min_volume = st.number_input('Minimum 24h volume ($)', min_value=0, value=5000, step=1000)
    max_age = st.number_input('Flag pairs younger than (hours)', min_value=0, value=2, step=1)
    max_liq_ratio = st.slider('Flag volume/liquidity ratio above', 0.5, 20.0, 5.0, 0.5)
    st.divider()
    st.subheader('Live execution')
    st.text('DISABLED — no wallet key is read or stored.')
    st.caption('Never paste a seed phrase or private key into this dashboard.')
    if st.button('Reset paper account', type='secondary'):
        state.clear(); state.update({'starting_balance':float(starting),'cash':float(starting),'trades':[]}); save_state(); st.rerun()
    if st.button('Apply starting balance'):
        if not trades:
            state['starting_balance'] = float(starting); state['cash'] = float(starting); save_state(); st.rerun()
        else: st.info('Reset the paper account first to change its starting balance.')

cfg = RiskConfig(min_liquidity=float(min_liq), min_volume_24h=float(min_volume), flag_pair_age_hours=float(max_age), max_volume_liquidity_ratio=float(max_liq_ratio))

tab_scan, tab_positions, tab_logs, tab_notes = st.tabs(['🔎 Scanner & Risk Check','📊 Paper positions','🧾 Trade log','🛠️ Setup notes'])
with tab_scan:
    c1,c2 = st.columns([3,1])
    with c1: query = st.text_input('Search Solana tokens / pairs', value='BONK', help='Search by token name or ticker using DexScreener public market data.')
    with c2:
        st.write('')
        do_search = st.button('Scan market', type='primary', use_container_width=True)
    token_addr = st.text_input('Or check a specific Solana token mint address', value='')
    if do_search or 'scan_results' not in st.session_state:
        with st.spinner('Fetching public pair data…'):
            st.session_state.scan_results = fetch_token(token_addr) if token_addr.strip() else fetch_search(query or 'BONK')
    pairs = st.session_state.get('scan_results', [])
    if pairs:
        rows=[]
        for p in pairs:
            risk = assess_pair(p, cfg)
            base = p.get('baseToken') or {}; quote = p.get('quoteToken') or {}; liq=(p.get('liquidity') or {})
            rows.append({'Token':base.get('symbol','?'),'Pair':f"{base.get('symbol','?')}/{quote.get('symbol','?')}",'Price USD':num(p.get('priceUsd')),'Liquidity $':num(liq.get('usd')),'Volume 24h $':num((p.get('volume') or {}).get('h24')),'Change 24h %':num((p.get('priceChange') or {}).get('h24')),'Pair age h':risk['pair_age_hours'],'Risk':risk['level'],'Risk flags':'; '.join(risk['flags']) or 'No basic flags','Mint':base.get('address',''),'URL':p.get('url','')})
        df=pd.DataFrame(rows).sort_values('Volume 24h $',ascending=False)
        st.dataframe(df[['Token','Pair','Price USD','Liquidity $','Volume 24h $','Change 24h %','Pair age h','Risk','Risk flags']], use_container_width=True, hide_index=True)
        st.caption('Risk checks are heuristics, not a guarantee that a token is safe. Public market data can be delayed or incomplete.')
        options={f"{r['Pair']} | liq ${r['Liquidity $']:,.0f} | {r['Risk']}":r for r in rows}
        selected_label=st.selectbox('Select token for a paper trade', list(options.keys()))
        selected=options[selected_label]
        a,b,c=st.columns(3)
        with a: st.write(f"**Mint:** `{selected['Mint']}`")
        with b: st.write(f"**Price:** ${selected['Price USD']:.10f}")
        with c:
            if selected['URL']: st.markdown(f"[Open pair chart]({selected['URL']})")
        st.subheader('Open a paper position')
        size_default=max(1.0, min(cash, equity*max_trade_pct/100))
        with st.form('paper_entry'):
            trade_size=st.number_input('Position size ($)', min_value=1.0, max_value=max(1.0,float(max(cash,1))), value=float(min(size_default,max(cash,1))), step=1.0)
            take_profit=st.number_input('Take-profit move (%)', min_value=1.0, max_value=500.0, value=20.0, step=1.0)
            stop_loss=st.number_input('Stop-loss move (%)', min_value=1.0, max_value=90.0, value=10.0, step=1.0)
            allow_flagged=st.checkbox('I understand this is only a simulation; allow a paper entry despite risk flags')
            submitted=st.form_submit_button('Open PAPER LONG')
        if submitted:
            open_count=sum(1 for t in state['trades'] if t.get('status')=='OPEN')
            reasons=[]
            if selected['Price USD']<=0: reasons.append('Price unavailable')
            if trade_size>cash: reasons.append('Insufficient paper cash')
            if trade_size>equity*max_trade_pct/100+1e-8: reasons.append('Position exceeds configured max trade size')
            if open_count>=max_open: reasons.append('Max open positions reached')
            if selected['Risk']!='LOW' and not allow_flagged: reasons.append('Risk flags present; check the override box to simulate anyway')
            if reasons: st.error('Entry blocked: ' + ' • '.join(reasons))
            else:
                state['cash']=round(cash-trade_size,8)
                state['trades'].append({'id':int(time.time()*1000),'time':datetime.now(timezone.utc).isoformat(),'symbol':selected['Token'],'mint':selected['Mint'],'entry_price':selected['Price USD'],'current_price':selected['Price USD'],'size_usd':trade_size,'tp_pct':take_profit,'sl_pct':stop_loss,'status':'OPEN','pnl':0.0,'risk':selected['Risk'],'source':'PAPER'})
                save_state(); st.success('Paper position opened. No blockchain transaction was sent.'); st.rerun()
    else:
        st.info('No Solana pairs found for this search. Try a ticker such as BONK, WIF, POPCAT, or paste a token mint address.')

with tab_positions:
    open_trades=[t for t in trades if t.get('status')=='OPEN']
    if not open_trades: st.info('No open paper positions yet. Use Scanner & Risk Check to open one.')
    else:
        for t in open_trades:
            with st.container(border=True):
                st.write(f"**{t['symbol']}** · ${num(t['size_usd']):.2f} position · risk {t.get('risk','?')}")
                st.caption(f"Mint: {t.get('mint','')}")
                price=st.number_input(f"Update price for {t['symbol']} (USD)", min_value=0.0, value=float(num(t.get('current_price'))), format='%.12f', key=f"price_{t['id']}")
                move=((price/num(t['entry_price']))-1)*100 if num(t['entry_price']) else 0
                pnl=num(t['size_usd'])*move/100
                x,y,z=st.columns(3); x.metric('Price move',f'{move:+.2f}%'); y.metric('Estimated P&L',f'${pnl:+.2f}'); z.metric('TP / SL',f"+{t['tp_pct']:.1f}% / -{t['sl_pct']:.1f}%")
                if move>=num(t['tp_pct']): st.success('Take-profit threshold reached (manual paper close available).')
                if move<=-num(t['sl_pct']): st.error('Stop-loss threshold reached (manual paper close available).')
                close_col, refresh_col=st.columns(2)
                if close_col.button('Close paper position',key=f"close_{t['id']}"):
                    t['current_price']=price; t['pnl']=round(pnl,8); t['status']='CLOSED'; t['closed_at']=datetime.now(timezone.utc).isoformat(); state['cash']=round(num(state['cash'])+num(t['size_usd'])+pnl,8); save_state(); st.rerun()
                if refresh_col.button('Save simulated price',key=f"save_{t['id']}"):
                    t['current_price']=price; t['pnl']=round(pnl,8); save_state(); st.rerun()

with tab_logs:
    if trades:
        logdf=pd.DataFrame(trades)
        cols=[c for c in ['time','closed_at','symbol','mint','entry_price','current_price','size_usd','pnl','status','risk','source'] if c in logdf.columns]
        st.dataframe(logdf[cols].sort_values('time',ascending=False), use_container_width=True, hide_index=True)
        st.download_button('Download trade log CSV', logdf[cols].to_csv(index=False).encode(), 'mafe_solana_trade_log.csv', 'text/csv')
    else: st.info('No trades logged yet.')

with tab_notes:
    st.markdown('''### Starter build status
- **Working:** Solana pair search via DexScreener public API, basic liquidity/volume/age checks, configurable paper position limits, simulated entries/exits, CSV logs.
- **Not implemented:** AI prediction claims, reliable scam detection, Jupiter swap execution, wallet signing, on-chain stop-loss monitoring, priority-fee handling, transaction reconciliation.
- **Before any live deployment:** add a separate signer service, use a dedicated low-balance wallet, never store a seed phrase in the app or `.env`, add transaction simulation and allowlists, cap daily loss, test on devnet/paper mode, and require explicit live-mode confirmation.

### Risk limitation
This scanner is not financial advice and its flags cannot establish that a meme coin is safe. Liquidity can disappear, token prices can move sharply, and on-chain swaps can fail or suffer slippage. Never use money you cannot afford to lose.
''')

st.caption('Market data: DexScreener public API. Paper-trading prices are refreshed only when you scan or manually update a position; this is not a real-time execution engine.')
