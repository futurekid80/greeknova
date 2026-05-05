import sys, time
sys.path.insert(0, '/Users/apple/optionspulse')
from dotenv import load_dotenv
load_dotenv('/Users/apple/optionspulse/.env')
from backend.services.kite_auth import get_kite_client
from backend.utils.db import get_supabase
from datetime import datetime, timezone

INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY"]
TOP30 = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK",
    "HINDUNILVR","ITC","SBIN","BHARTIARTL","KOTAKBANK",
    "LT","AXISBANK","ASIANPAINT","MARUTI","TITAN",
    "SUNPHARMA","ULTRACEMCO","BAJFINANCE","WIPRO","HCLTECH",
    "TATACONSUM","TATASTEEL","ADANIENT","POWERGRID","NTPC",
    "ONGC","JSWSTEEL","COALINDIA","BAJAJFINSV","TECHM"
]
INDEX_NSE_MAP = {
    "NIFTY":"NSE:NIFTY 50",
    "BANKNIFTY":"NSE:NIFTY BANK",
    "FINNIFTY":"NSE:NIFTY FIN SERVICE"
}
STOCK_NSE_MAP = {
    "RELIANCE":"NSE:RELIANCE","TCS":"NSE:TCS","HDFCBANK":"NSE:HDFCBANK",
    "INFY":"NSE:INFY","ICICIBANK":"NSE:ICICIBANK","HINDUNILVR":"NSE:HINDUNILVR",
    "ITC":"NSE:ITC","SBIN":"NSE:SBIN","BHARTIARTL":"NSE:BHARTIARTL",
    "KOTAKBANK":"NSE:KOTAKBANK","LT":"NSE:LT","AXISBANK":"NSE:AXISBANK",
    "ASIANPAINT":"NSE:ASIANPAINT","MARUTI":"NSE:MARUTI","TITAN":"NSE:TITAN",
    "SUNPHARMA":"NSE:SUNPHARMA","ULTRACEMCO":"NSE:ULTRACEMCO","BAJFINANCE":"NSE:BAJFINANCE",
    "WIPRO":"NSE:WIPRO","HCLTECH":"NSE:HCLTECH","TATACONSUM":"NSE:TATACONSUM",
    "TATASTEEL":"NSE:TATASTEEL","ADANIENT":"NSE:ADANIENT","POWERGRID":"NSE:POWERGRID",
    "NTPC":"NSE:NTPC","ONGC":"NSE:ONGC","JSWSTEEL":"NSE:JSWSTEEL",
    "COALINDIA":"NSE:COALINDIA","BAJAJFINSV":"NSE:BAJAJFINSV","TECHM":"NSE:TECHM"
}

kite = get_kite_client()
supabase = get_supabase()
timestamp = datetime.now(timezone.utc).isoformat()
records = []
cmp_records = []

print("💰 Fetching live CMPs...")
try:
    idx_quotes = kite.quote(list(INDEX_NSE_MAP.values()))
    for sym, key in INDEX_NSE_MAP.items():
        price = idx_quotes.get(key, {}).get("last_price", 0)
        if price:
            cmp_records.append({"timestamp": timestamp, "symbol": sym, "cmp": float(price)})
            print(f"  ✅ {sym}: {price}")
except Exception as e:
    print(f"  ⚠️ Index CMP error: {e}")

try:
    stk_quotes = kite.quote(list(STOCK_NSE_MAP.values()))
    for sym, key in STOCK_NSE_MAP.items():
        price = stk_quotes.get(key, {}).get("last_price", 0)
        if price:
            cmp_records.append({"timestamp": timestamp, "symbol": sym, "cmp": float(price)})
    print(f"  ✅ {len([c for c in cmp_records if c['symbol'] in TOP30])} stock CMPs fetched")
except Exception as e:
    print(f"  ⚠️ Stock CMP error: {e}")

print("📋 Loading OI instruments...")
instruments = kite.instruments("NFO")

for symbol in INDICES + TOP30:
    is_index = symbol in INDICES
    limit = 40 if is_index else 20
    found = [i for i in instruments if i["name"] == symbol and i["instrument_type"] in ["CE","PE"]]
    if not found:
        print(f"  ⚠️ {symbol} not found"); continue
    expiries = sorted(set(i["expiry"] for i in found))
    nearest = [i for i in found if i["expiry"] == expiries[0]][:limit]
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
                    "is_index": is_index,
                })
        print(f"  ✅ {symbol}: {len(nearest)} strikes")
        time.sleep(0.3)
    except Exception as e:
        print(f"  ❌ {symbol}: {e}")

if records:
    for i in range(0, len(records), 500):
        supabase.table("oi_snapshots").insert(records[i:i+500]).execute()
    print(f"\n✅ Saved {len(records)} OI records")

if cmp_records:
    supabase.table("cmp_prices").insert(cmp_records).execute()
    print(f"✅ Saved {len(cmp_records)} CMP prices")
    for c in cmp_records[:5]:
        print(f"   {c['symbol']}: ₹{c['cmp']}")
