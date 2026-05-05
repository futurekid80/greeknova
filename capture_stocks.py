import sys
sys.path.insert(0, '/Users/apple/optionspulse')

from dotenv import load_dotenv
load_dotenv('/Users/apple/optionspulse/.env')

from backend.services.kite_auth import get_kite_client
from backend.utils.db import get_supabase
from datetime import datetime

TOP30 = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK",
    "HINDUNILVR","ITC","SBIN","BHARTIARTL","KOTAKBANK",
    "LT","AXISBANK","ASIANPAINT","MARUTI","TITAN",
    "SUNPHARMA","ULTRACEMCO","BAJFINANCE","WIPRO","HCLTECH",
    "TATACONSUM","TATASTEEL","ADANIENT","POWERGRID","NTPC",
    "ONGC","JSWSTEEL","COALINDIA","BAJAJFINSV","TECHM"
]

kite = get_kite_client()
supabase = get_supabase()
print("📋 Loading instruments...")
instruments = kite.instruments("NFO")
timestamp = datetime.now().isoformat()
records = []

for symbol in TOP30:
    found = [i for i in instruments if i["name"] == symbol and i["instrument_type"] in ["CE","PE"]]
    if not found:
        print(f"  ⚠️  {symbol} not found"); continue
    expiries = sorted(set(i["expiry"] for i in found))
    nearest = [i for i in found if i["expiry"] == expiries[0]][:20]
    try:
        quotes = kite.quote(["NFO:" + i["tradingsymbol"] for i in nearest])
        for inst in nearest:
            key = f"NFO:{inst['tradingsymbol']}"
            if key in quotes:
                q = quotes[key]
                records.append({
                    "timestamp": timestamp, "symbol": symbol,
                    "tradingsymbol": inst["tradingsymbol"],
                    "strike": float(inst["strike"]),
                    "option_type": inst["instrument_type"],
                    "expiry": inst["expiry"].isoformat(),
                    "oi": int(q.get("oi", 0)),
                    "oi_day_high": int(q.get("oi_day_high", 0)),
                    "volume": int(q.get("volume", 0)),
                    "last_price": float(q.get("last_price", 0)),
                    "is_index": False,
                })
        print(f"  ✅ {symbol}: {len(nearest)} strikes")
    except Exception as e:
        print(f"  ❌ {symbol}: {e}")

if records:
    for i in range(0, len(records), 500):
        supabase.table("oi_snapshots").insert(records[i:i+500]).execute()
    print(f"\n✅ Saved {len(records)} records!")
else:
    print("❌ No records saved")
