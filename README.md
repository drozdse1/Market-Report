# Market Report

Weekly Market Health Report that automates a "state check" of the 4 hidden
forces that have been holding up the stock market. Based on the YouTube video
https://youtu.be/3d6fBX99lAw by Felix Prehn (Goat Academy).

## The 4 Forces + Yield Curve

| Force | What it measures | Indicators used |
|---|---|---|
| **1. Fed Put** | Can the Fed still bail out the market? | VIX, CPI YoY (or Oil proxy), 10Y Treasury yield |
| **2. Passive Money Machine** | Are 401k inflows still strong? | Unemployment + 3mo change (Sahm rule), or HYG/LQD credit spread, or SPX vs 200DMA |
| **3. Algorithms (CTAs)** | Are trend-followers buying or selling? | SPX vs 50DMA & 200DMA, VIX regime |
| **4. Options / Retail** | Is there panic or complacency? | Put/Call ratio (^CPC) with VIX fallback |
| *Bonus: Yield Curve* | Recession precursor | 10Y − 3M Treasury spread |

Each force is rated `++ / + / 0 / - / --` and aggregated into an overall
assessment: **Very Stable / Stable / Neutral / Caution / High Risk**.

## Usage

```bash
pip install -r requirements.txt
python weekly_market_health.py
```

The script writes `market_health_report.txt` and prints it to stdout.

### Optional: FRED Integration (recommended)

For real unemployment & CPI data (instead of proxies), set a free FRED API key:

```bash
export FRED_API_KEY="your_key_here"
python weekly_market_health.py
```

Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html

**If the key is not set**, the script still runs but shows a warning and falls
back to proxies (oil price for inflation, credit spreads / 200DMA for jobs).

## Example Output

```
Market Health Report – 30.04.2026
=================================================================

[WARNING] FRED_API_KEY not set -> using proxies (oil for CPI, 200DMA for
unemployment). Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html

Overall Assessment: + Stable  (Score: 3)

Rating of the 4 Forces (+ Yield Curve):
  Fed Put            : -
  Passive            : ++
  Algos              : +
  Options            : 0
  YieldCurve         : +

Key Indicators:
  SPX_Price         : 7135.95
  SPX_50DMA         : 6808.0
  SPX_200DMA        : 6718.79
  VIX               : 18.43
  TNX_10Y           : 4.418
  FVX_5Y            : 4.065
  IRX_3M            : 3.59
  Oil_WTI           : 107.76
  YieldCurve        : 0.828
  HYG_LQD           : 0.737
  Credit_20dChg_%   : 0.89
  Above_200DMA      : True
  Above_50DMA       : True
```

## Requirements

- Python 3.12+
- pandas, yfinance, fredapi (see `requirements.txt`)

## Disclaimer

Educational tool only. Not financial advice.
