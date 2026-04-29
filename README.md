# Market Report

Weekly Market Health Report based on 4 key market forces:
- Earnings growth
- Interest rates
- Liquidity
- Sentiment

Based on the Youtube video https://youtu.be/3d6fBX99lAw?is=8y61e3a0gEjmKJqr (Felix Prehn)

## Usage

```bash
python weekly_market_health.py
```

## Example Output

```
Market Health Report – 29.04.2026
=================================================================

Overall Assessment: - Caution  (Score: -3)

Rating of the 4 Forces:
  Fed Put            : -
  Passive            : -
  Algos              : --
  Options            : +

Key Indicators:
  SPX_Price      : 7138.8
  VIX            : 18.05
  TNX            : 4.354
  Oil            : 103.49
  Above_200DMA   : False
```

## Requirements

- Python 3.12+
- pandas, yfinance
