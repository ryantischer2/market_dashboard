"""
Scan a broad universe of stocks for those within 3% of their 200 DMA.
Updates the "At 200 DMA" list in build_data.py, then rebuilds the dashboard.
Run: python scripts/update_200dma.py
"""
import re, sys, os
import yfinance as yf

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
    'GRAB','SQ','BILL','FOUR',
    # Popular mid-caps
    'CELH','HIMS','RKLB','IONQ','RGTI','APP','DUOL','TTD',
]

THRESHOLD_PCT = 3.0
BUILD_SCRIPT = os.path.join(os.path.dirname(__file__), 'build_data.py')

def scan():
    results = []
    for t in UNIVERSE:
        try:
            hist = yf.Ticker(t).history(period='1y')
            if len(hist) < 200:
                continue
            sma200 = hist['Close'].rolling(200).mean().iloc[-1]
            price = hist['Close'].iloc[-1]
            pct = ((price - sma200) / sma200) * 100
            if abs(pct) <= THRESHOLD_PCT:
                results.append((t, round(pct, 2)))
        except Exception:
            pass
    results.sort(key=lambda x: abs(x[1]))
    return [r[0] for r in results]

def update_build_script(tickers):
    with open(BUILD_SCRIPT, 'r') as f:
        content = f.read()
    # Replace the At 200 DMA list
    pattern = r'("At 200 DMA":\s*\[)[^\]]*(\])'
    replacement = r'\1' + ', '.join(f'"{t}"' for t in tickers) + r'\2'
    new_content = re.sub(pattern, replacement, content)
    with open(BUILD_SCRIPT, 'w') as f:
        f.write(new_content)
    print(f"Updated At 200 DMA: {tickers}")

if __name__ == '__main__':
    tickers = scan()
    if tickers:
        update_build_script(tickers)
    else:
        print("No stocks within threshold — keeping existing list")
