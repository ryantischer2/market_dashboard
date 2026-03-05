"""
Scan stocks using Finviz-style criteria and update build_data.py groups.
Groups:
  - "S/D Pullbacks": Quarter up 10%+, week down, price>$20, optionable, volume>400K
  - "Squeeze Setups": Month up 10%+, relative volume>1, short float>20%, optionable
  - "At 200 DMA": Within 3% of 200 SMA
Run: python scripts/update_200dma.py
"""
import re, os, json
import yfinance as yf
import numpy as np

BUILD_SCRIPT = os.path.join(os.path.dirname(__file__), 'build_data.py')

# Broad universe to scan
UNIVERSE = [
    # Mega cap / tech
    'AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','AMD','NFLX','CRM',
    'AVGO','ORCL','ADBE','INTC','CSCO','QCOM','MU','AMAT','LRCX','KLAC',
    'NOW','PANW','CRWD','SNOW','PLTR','COIN','MSTR','PYPL','SHOP',
    # Financials
    'JPM','BAC','GS','MS','V','MA','AXP','WFC','C','BX','SOFI','HOOD','NU','AFRM','UPST',
    # Healthcare
    'UNH','JNJ','PFE','ABBV','LLY','MRK','BMY','AMGN','GILD','TMO',
    # Energy
    'XOM','CVX','COP','SLB','OXY','DVN','EOG','MPC','PSX','VLO',
    # Industrials
    'CAT','DE','HON','GE','RTX','LMT','BA','UNP','FDX','UPS',
    # Consumer
    'HD','LOW','NKE','SBUX','MCD','DIS','ABNB','BKNG','MAR','CMG',
    'WMT','COST','TGT','PG','KO','PEP','CL','EL','MDLZ','GIS',
    # Utilities / REITs
    'NEE','DUK','SO','AEP','SPG','PLD','AMT','CCI','EQIX','O',
    # Telecom
    'T','VZ','TMUS','CMCSA','CHTR',
    # EV / Auto
    'F','GM','RIVN','LCID','LI','NIO','XPEV',
    # Semis
    'ARM','SMCI','DELL','HPE','MRVL','ON','MPWR','TXN',
    # Solar / Clean
    'RUN','ENPH','FSLR','SEDG',
    # Fintech / Growth
    'GRAB','BILL','FOUR',
    # Popular mid-caps / meme / squeeze candidates
    'CELH','HIMS','RKLB','IONQ','RGTI','APP','DUOL','TTD',
    'GME','AMC','BBBY','CLOV','WISH','SPCE','BYND','CVNA','UPWK',
    'DKNG','ROKU','SNAP','PINS','LYFT','UBER','PATH','DOCS',
    'CROX','BIRK','DASH','RBLX','U','ZS','OKTA','DDOG','NET',
    'WOLF','PLUG','FCEL','CHPT','QS','LAZR','STEM',
    'SQ','OPEN','LMND','ROOT','ACHR','JOBY','LILM',
    'MARA','RIOT','CLSK','HUT','BITF','IREN',
    'SMMT','RXRX','DNA','CRSP','NTLA','BEAM','EDIT',
    'EWX','GRTS','LQDA','ACLS',  # tickers from the video
    # 200 SMA bounce candidates (Mar 4 2026)
    'ZM','HASI','BE','MP','QRVO','GRMN','ALSN',
]

# Deduplicate
UNIVERSE = list(dict.fromkeys(UNIVERSE))


def get_stock_data(ticker):
    """Fetch 1y history + info for a ticker."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period='1y')
        if len(hist) < 20:
            return None
        info = tk.info or {}
        return tk, hist, info
    except Exception:
        return None


def scan_sd_pullbacks():
    """Scan 1: Supply/Demand Pullbacks
    - Price > $20
    - Optionable (has options)
    - Avg volume > 400K
    - Quarter up 10%+
    - Week down (any amount)
    """
    results = []
    for t in UNIVERSE:
        data = get_stock_data(t)
        if not data:
            continue
        tk, hist, info = data
        price = hist['Close'].iloc[-1]

        # Price > $20
        if price < 20:
            continue

        # Volume > 400K avg
        avg_vol = hist['Volume'].tail(20).mean()
        if avg_vol < 400000:
            continue

        # Quarter performance: up 10%+
        if len(hist) >= 63:
            qtr_ago = hist['Close'].iloc[-63]
            qtr_perf = ((price - qtr_ago) / qtr_ago) * 100
        else:
            continue
        if qtr_perf < 10:
            continue

        # Week performance: down
        if len(hist) >= 5:
            week_ago = hist['Close'].iloc[-5]
            week_perf = ((price - week_ago) / week_ago) * 100
        else:
            continue
        if week_perf >= 0:
            continue

        # Check optionable
        try:
            opts = tk.options
            if not opts or len(opts) == 0:
                continue
        except Exception:
            continue

        results.append((t, round(qtr_perf, 1), round(week_perf, 1)))
        print(f"  S/D Pullback: {t} (qtr +{qtr_perf:.1f}%, wk {week_perf:.1f}%)")

    # Sort by quarter performance descending
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]


def scan_squeeze():
    """Scan 2: Short Squeeze Setups
    - Optionable
    - Month up 10%+
    - Relative volume > 1 (today's vol vs 20d avg)
    - Short float > 20%
    """
    results = []
    for t in UNIVERSE:
        data = get_stock_data(t)
        if not data:
            continue
        tk, hist, info = data
        price = hist['Close'].iloc[-1]

        # Month performance: up 10%+
        if len(hist) >= 21:
            month_ago = hist['Close'].iloc[-21]
            month_perf = ((price - month_ago) / month_ago) * 100
        else:
            continue
        if month_perf < 10:
            continue

        # Relative volume > 1
        if len(hist) >= 21:
            avg_vol_20d = hist['Volume'].tail(20).mean()
            last_vol = hist['Volume'].iloc[-1]
            if avg_vol_20d > 0:
                rel_vol = last_vol / avg_vol_20d
            else:
                continue
        else:
            continue
        if rel_vol < 1.0:
            continue

        # Short float > 20%
        short_pct = info.get('shortPercentOfFloat', 0) or 0
        # yfinance returns as decimal (0.25 = 25%) or percentage depending on version
        if short_pct > 1:
            short_pct_display = short_pct
        else:
            short_pct_display = short_pct * 100
        if short_pct_display < 20:
            continue

        # Optionable
        try:
            opts = tk.options
            if not opts or len(opts) == 0:
                continue
        except Exception:
            continue

        results.append((t, round(month_perf, 1), round(short_pct_display, 1), round(rel_vol, 2)))
        print(f"  Squeeze: {t} (mo +{month_perf:.1f}%, short {short_pct_display:.1f}%, relvol {rel_vol:.1f}x)")

    results.sort(key=lambda x: x[2], reverse=True)  # sort by short %
    return [r[0] for r in results]


def scan_200dma():
    """Within 3% of 200 SMA."""
    results = []
    for t in UNIVERSE:
        data = get_stock_data(t)
        if not data:
            continue
        tk, hist, info = data
        if len(hist) < 200:
            continue
        sma200 = hist['Close'].rolling(200).mean().iloc[-1]
        price = hist['Close'].iloc[-1]
        pct = ((price - sma200) / sma200) * 100
        if abs(pct) <= 3.0:
            results.append((t, round(pct, 2)))
            print(f"  200 DMA: {t} ({pct:+.2f}%)")
    results.sort(key=lambda x: abs(x[1]))
    return [r[0] for r in results]


def update_group(content, group_name, tickers):
    """Update a single group's ticker list in build_data.py content."""
    pattern = r'("' + re.escape(group_name) + r'":\s*\[)[^\]]*(\])'
    if tickers:
        replacement = r'\g<1>' + ', '.join(f'"{t}"' for t in tickers) + r'\2'
    else:
        replacement = r'\g<1>' + r'\2'
    new_content = re.sub(pattern, replacement, content)
    return new_content


def ensure_group_exists(content, group_name):
    """Add group to STOCK_GROUPS if not present."""
    if f'"{group_name}"' in content:
        return content
    # Insert before the closing brace of STOCK_GROUPS
    content = content.replace(
        '\n}',
        f',\n    "{group_name}": []\n}}',
        1
    )
    return content


if __name__ == '__main__':
    with open(BUILD_SCRIPT, 'r') as f:
        content = f.read()

    print("Scanning S/D Pullbacks...")
    sd_tickers = scan_sd_pullbacks()
    print(f"Found {len(sd_tickers)} S/D Pullback stocks\n")

    print("Scanning Squeeze Setups...")
    sq_tickers = scan_squeeze()
    print(f"Found {len(sq_tickers)} Squeeze stocks\n")

    print("Scanning At 200 DMA...")
    dma_tickers = scan_200dma()
    print(f"Found {len(dma_tickers)} stocks at 200 DMA\n")

    # Ensure groups exist
    for g in ["S/D Pullbacks", "Squeeze Setups", "At 200 DMA"]:
        content = ensure_group_exists(content, g)

    # Update groups (only if we found tickers)
    if sd_tickers:
        content = update_group(content, "S/D Pullbacks", sd_tickers)
    if sq_tickers:
        content = update_group(content, "Squeeze Setups", sq_tickers)
    if dma_tickers:
        content = update_group(content, "At 200 DMA", dma_tickers)

    with open(BUILD_SCRIPT, 'w') as f:
        f.write(content)

    print("Done! Updated build_data.py")
