#!/usr/bin/env python3.12
"""
Weekly Market Health Report
Based on the 4 forces from the video "Why the Stock Market REFUSES to Crash"

Forces tracked:
  1. Fed Put        -> VIX, Oil (inflation proxy), 10Y Treasury yield
  2. Passive Money  -> SPX vs 200DMA + 50DMA trend (jobs proxy: HYG/LQD credit spread)
  3. Algorithms     -> SPX trend (200DMA + 50DMA) + VIX regime
  4. Options/Retail -> Put/Call ratio (^CPC), fallback to VIX term structure
"""

import os
import warnings
import logging
import pandas as pd
import yfinance as yf
from datetime import datetime

try:
    from fredapi import Fred
except ImportError:
    Fred = None

REPORT_FILE = "market_health_report.txt"
FRED_API_KEY = os.environ.get("FRED_API_KEY")


def _last(series):
    """Return the last non-NaN value of a series, or None."""
    s = series.dropna()
    return float(s.iloc[-1]) if len(s) else None


def _safe_fetch(ticker, period="1y"):
    try:
        return yf.Ticker(ticker).history(period=period)["Close"]
    except Exception:
        return pd.Series(dtype=float)


def _quiet_fetch(ticker, period="1y"):
    """Fetch with all warnings/logging suppressed (for known-broken tickers)."""
    import io, sys
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _yf_logger = logging.getLogger("yfinance")
        _prev = _yf_logger.level
        _yf_logger.setLevel(logging.CRITICAL)
        _old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            result = _safe_fetch(ticker, period)
        finally:
            sys.stderr = _old_stderr
            _yf_logger.setLevel(_prev)
    return result


def _fetch_fred():
    """Fetch macro indicators from FRED. Returns {} if no key / library."""
    out = {}
    if Fred is None:
        out["_FRED_Warning"] = "fredapi not installed -> run: pip install fredapi"
        return out
    if not FRED_API_KEY:
        out["_FRED_Warning"] = (
            "FRED_API_KEY not set -> using proxies (oil for CPI, 200DMA for unemployment). "
            "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
        return out
    try:
        fred = Fred(api_key=FRED_API_KEY)
        unrate = fred.get_series("UNRATE").dropna()          # Unemployment rate %
        cpi    = fred.get_series("CPIAUCSL").dropna()        # CPI index
        if len(unrate):
            out["Unemployment_%"] = round(float(unrate.iloc[-1]), 2)
            if len(unrate) >= 4:
                out["Unemp_3mo_chg"] = round(float(unrate.iloc[-1] - unrate.iloc[-4]), 2)
        if len(cpi) >= 13:
            yoy = (cpi.iloc[-1] / cpi.iloc[-13] - 1) * 100
            out["CPI_YoY_%"] = round(float(yoy), 2)
    except Exception as e:
        out["FRED_Error"] = str(e)
    return out


def get_market_data():
    data = {}
    try:
        spx = _safe_fetch("^GSPC", "2y")
        vix = _safe_fetch("^VIX", "3mo")
        tnx = _safe_fetch("^TNX", "3mo")   # 10Y yield
        fvx = _safe_fetch("^FVX", "3mo")   # 5Y yield
        irx = _safe_fetch("^IRX", "3mo")   # 3M yield (2Y proxy)
        oil = _safe_fetch("CL=F", "3mo")
        pcr = _quiet_fetch("^CPC", "1mo")  # delisted on Yahoo; suppressed
        hyg = _safe_fetch("HYG", "3mo")    # junk bond ETF
        lqd = _safe_fetch("LQD", "3mo")    # investment grade ETF

        data["SPX_Price"]  = round(_last(spx), 2) if _last(spx) else None
        data["SPX_50DMA"]  = round(spx.rolling(50).mean().iloc[-1], 2)  if len(spx) >= 50  else None
        data["SPX_200DMA"] = round(spx.rolling(200).mean().iloc[-1], 2) if len(spx) >= 200 else None
        data["VIX"]        = round(_last(vix), 2) if _last(vix) else None
        data["TNX_10Y"]    = round(_last(tnx), 3) if _last(tnx) else None
        data["FVX_5Y"]     = round(_last(fvx), 3) if _last(fvx) else None
        data["IRX_3M"]     = round(_last(irx), 3) if _last(irx) else None
        data["Oil_WTI"]    = round(_last(oil), 2) if _last(oil) else None
        data["PutCall"]    = round(_last(pcr), 3) if _last(pcr) else None

        # Yield curve (10Y - 3M). Negative = inverted = recession signal.
        if data["TNX_10Y"] is not None and data["IRX_3M"] is not None:
            data["YieldCurve"] = round(data["TNX_10Y"] - data["IRX_3M"], 3)
        else:
            data["YieldCurve"] = None

        # Credit spread proxy: HYG/LQD ratio. Falling ratio = credit stress.
        if _last(hyg) and _last(lqd):
            data["HYG_LQD"] = round(_last(hyg) / _last(lqd), 4)
            # 20-day change to detect stress
            if len(hyg) >= 20 and len(lqd) >= 20:
                ratio_now = hyg.iloc[-1] / lqd.iloc[-1]
                ratio_20d = hyg.iloc[-20] / lqd.iloc[-20]
                data["Credit_20dChg_%"] = round((ratio_now / ratio_20d - 1) * 100, 2)
            else:
                data["Credit_20dChg_%"] = None
        else:
            data["HYG_LQD"] = None
            data["Credit_20dChg_%"] = None

        # Trend flags
        data["Above_200DMA"] = (data["SPX_Price"] is not None
                                and data["SPX_200DMA"] is not None
                                and data["SPX_Price"] > data["SPX_200DMA"])
        data["Above_50DMA"]  = (data["SPX_Price"] is not None
                                and data["SPX_50DMA"] is not None
                                and data["SPX_Price"] > data["SPX_50DMA"])

        # Optional FRED macro indicators
        data.update(_fetch_fred())

    except Exception as e:
        print(f"Error fetching market data: {e}")
        data["Error"] = str(e)

    return data


def evaluate_indicators(data):
    ratings = {}

    vix   = data.get("VIX") or 0
    oil   = data.get("Oil_WTI") or 0
    tnx   = data.get("TNX_10Y") or 0
    curve = data.get("YieldCurve")
    pcr   = data.get("PutCall")
    credit_chg = data.get("Credit_20dChg_%")
    cpi   = data.get("CPI_YoY_%")           # real inflation, if available
    unemp = data.get("Unemployment_%")
    unemp_chg = data.get("Unemp_3mo_chg")

    # --- 1. Fed Put ---
    # Real CPI overrides oil-based inflation proxy when available
    fed_score = 0
    inflation_hot = (cpi is not None and cpi > 4.0) or (cpi is None and oil > 110)
    inflation_warm = (cpi is not None and cpi > 3.0) or (cpi is None and oil > 90)
    if vix > 30 or inflation_hot or tnx > 5.5:
        fed_score = -2
    elif vix > 22 or inflation_warm or tnx > 4.8:
        fed_score = -1
    elif vix < 18 and (cpi is None or cpi < 2.5) and tnx < 4.5:
        fed_score = 2
    else:
        fed_score = 1
    ratings["Fed_Put"] = _score_to_label(fed_score)

    # --- 2. Passive Money Machine ---
    # Real unemployment > credit spread > 200DMA (fallback hierarchy)
    passive_score = 0
    above_200 = data.get("Above_200DMA")
    if unemp is not None:
        # Sahm-rule style: 3mo rise of 0.5%+ is recession signal
        if unemp_chg is not None and unemp_chg >= 0.5:
            passive_score = -2
        elif unemp_chg is not None and unemp_chg >= 0.3:
            passive_score = -1
        elif unemp < 4.5:
            passive_score = 2
        else:
            passive_score = 1
    elif credit_chg is not None and credit_chg < -2:
        passive_score = -2
    elif credit_chg is not None and credit_chg < -0.5:
        passive_score = -1
    elif above_200 and (credit_chg is None or credit_chg > 0):
        passive_score = 2
    elif above_200:
        passive_score = 1
    else:
        passive_score = -1
    ratings["Passive"] = _score_to_label(passive_score)

    # --- 3. Algorithms / CTAs ---
    # Trend + volatility regime
    above_50  = data.get("Above_50DMA")
    if above_200 and above_50 and vix < 18:
        algo_score = 2
    elif above_200 and above_50:
        algo_score = 1
    elif above_200 and not above_50:
        algo_score = 0           # short-term weakness
    elif above_50 and not above_200:
        algo_score = -1          # bounce in downtrend
    else:
        algo_score = -2
    ratings["Algos"] = _score_to_label(algo_score)

    # --- 4. Options Market Makers & Retail ---
    # Put/Call ratio: high = fear (contrarian bullish), low = complacency
    if pcr is not None:
        if pcr > 1.20:
            opt_score = 2        # panic -> MMs forced buying
        elif pcr > 0.95:
            opt_score = 1
        elif pcr > 0.75:
            opt_score = 0
        elif pcr > 0.55:
            opt_score = -1       # complacency
        else:
            opt_score = -2       # extreme complacency
    else:
        # Fallback: VIX-based
        opt_score = 1 if vix < 18 else (-1 if vix > 25 else 0)
    ratings["Options"] = _score_to_label(opt_score)

    # --- Bonus signal: yield curve (not a "force" but strong crash precursor) ---
    if curve is not None:
        if curve < -0.5:
            ratings["YieldCurve"] = "--"   # strong inversion
        elif curve < 0:
            ratings["YieldCurve"] = "-"
        elif curve < 1:
            ratings["YieldCurve"] = "+"
        else:
            ratings["YieldCurve"] = "++"
    else:
        ratings["YieldCurve"] = "0"

    # Overall
    score_map = {"++": 2, "+": 1, "0": 0, "-": -1, "--": -2}
    total = sum(score_map.get(r, 0) for r in ratings.values())

    if total >= 7:
        overall = "++ Very Stable"
    elif total >= 3:
        overall = "+ Stable"
    elif total >= -2:
        overall = "0 Neutral"
    elif total >= -5:
        overall = "- Caution"
    else:
        overall = "-- High Risk"

    return ratings, overall, total


def _score_to_label(s):
    if s >= 2:  return "++"
    if s == 1:  return "+"
    if s == 0:  return "0"
    if s == -1: return "-"
    return "--"


def create_report():
    today = datetime.now()
    print(f"Starting Market Report: {today.strftime('%d.%m.%Y %H:%M')}")

    data = get_market_data()
    ratings, overall, total = evaluate_indicators(data)

    warning = data.pop("_FRED_Warning", None)
    if warning:
        print(f"\n[WARNING] {warning}\n")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"Market Health Report – {today.strftime('%d.%m.%Y')}\n")
        f.write("=" * 65 + "\n\n")
        if warning:
            f.write(f"[WARNING] {warning}\n\n")
        f.write(f"Overall Assessment: {overall}  (Score: {total})\n\n")

        f.write("Rating of the 4 Forces (+ Yield Curve):\n")
        for name, rating in ratings.items():
            f.write(f"  {name.replace('_', ' '):<18} : {rating}\n")

        f.write("\nKey Indicators:\n")
        for key, value in data.items():
            if value is not None and key != "Error" and not key.startswith("_"):
                f.write(f"  {key:<18}: {value}\n")

    print(f"\nReport successfully created: {REPORT_FILE}")
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        print("\n" + f.read())


if __name__ == "__main__":
    create_report()
