#!/usr/bin/env python3.12
"""
Weekly Market Health Report
Based on the 4 forces from the video "Why the Stock Market REFUSES to Crash"
"""

import pandas as pd
import yfinance as yf
from datetime import datetime
import sys

# ==================== CONFIGURATION ====================
REPORT_FILE = "market_health_report.txt"

def get_market_data():
    data = {}
    try:
        # Download latest data
        spx = yf.Ticker("^GSPC").history(period="3mo")["Close"]
        vix = yf.Ticker("^VIX").history(period="1mo")["Close"]
        tnx = yf.Ticker("^TNX").history(period="1mo")["Close"]
        oil = yf.Ticker("CL=F").history(period="1mo")["Close"]

        data["SPX_Price"] = round(spx.iloc[-1], 2)
        data["SPX_200DMA"] = round(spx.rolling(200).mean().iloc[-1], 2) if len(spx) >= 200 else None
        data["VIX"] = round(vix.iloc[-1], 2)
        data["TNX"] = round(tnx.iloc[-1], 3)
        data["Oil"] = round(oil.iloc[-1], 2)
        
        if data["SPX_200DMA"] is not None:
            data["Above_200DMA"] = data["SPX_Price"] > data["SPX_200DMA"]
        else:
            data["Above_200DMA"] = False

    except Exception as e:
        print(f"Error fetching market data: {e}")
        data["Error"] = str(e)
    
    return data


def evaluate_indicators(data):
    ratings = {}

    # 1. Fed Put
    if data.get("VIX", 0) > 35 or data.get("Oil", 0) > 110:
        ratings["Fed_Put"] = "--"
    elif data.get("VIX", 0) > 25 or data.get("Oil", 0) > 90:
        ratings["Fed_Put"] = "-"
    else:
        ratings["Fed_Put"] = "++"

    # 2. Passive Money Machine
    ratings["Passive"] = "++" if data.get("Above_200DMA") else "-"

    # 3. Algorithms / Trend Followers
    if data.get("Above_200DMA") and data.get("VIX", 0) < 20:
        ratings["Algos"] = "++"
    elif data.get("Above_200DMA"):
        ratings["Algos"] = "+"
    else:
        ratings["Algos"] = "--"

    # 4. Options Market Makers & Retail
    ratings["Options"] = "+"   # Can be extended later with Put/Call ratio

    # Overall Score
    score_map = {"++": 2, "+": 1, "-": -1, "--": -2}
    total_score = sum(score_map.get(r, 0) for r in ratings.values())

    if total_score >= 6:
        overall = "++ Very Stable"
    elif total_score >= 3:
        overall = "+ Stable"
    elif total_score >= -1:
        overall = "0 Neutral"
    elif total_score >= -4:
        overall = "- Caution"
    else:
        overall = "-- High Risk"

    return ratings, overall, total_score


def create_report():
    today = datetime.now()
    print(f"Starting Market Report: {today.strftime('%d.%m.%Y %H:%M')}")

    data = get_market_data()
    ratings, overall, total = evaluate_indicators(data)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"Market Health Report – {today.strftime('%d.%m.%Y')}\n")
        f.write("=" * 65 + "\n\n")
        f.write(f"Overall Assessment: {overall}  (Score: {total})\n\n")
        
        f.write("Rating of the 4 Forces:\n")
        for name, rating in ratings.items():
            f.write(f"  {name.replace('_', ' '):<18} : {rating}\n")
        
        f.write("\nKey Indicators:\n")
        for key, value in data.items():
            if value is not None and key != "Error":
                f.write(f"  {key:<15}: {value}\n")

    print(f"\nReport successfully created: {REPORT_FILE}")
    
    # Display the report
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        print("\n" + f.read())


if __name__ == "__main__":
    create_report()
