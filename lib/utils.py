import requests
import pandas as pd
import logging
from typing import Union, Literal, Tuple
import mplfinance as mpf
from datetime import datetime

# api.bitget.com
# [1min,3min,5min,15min,30min,1h,4h,6h,12h,1day,1week,1M,6Hutc,12Hutc,1Dutc,3Dutc,1Wutc,1Mutc]
GranularityType = Literal["1min", "3min", "5min", "15min", "30min", "1h", "4h", "6h", "12h", "1day", "1week", "1M", "6Hutc", "12Hutc", "1Dutc", "3Dutc", "1Wutc", "1Mutc"]
# 📈 Bitget’ten mumları alma (requests.get ile)
def get_candles(symbol: str = "BTCUSDT", granularity: GranularityType = "15min", limit: int = 200) -> Union[pd.DataFrame, None]:
    url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity={granularity}&limit={limit}"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
            # Data format may be list of lists (timestamp,open,high,low,close,volume,...)
            # Ensure we convert correctly.
            df = pd.DataFrame(data["data"])
            # If API returns more than 6 columns, take first 6 expected columns
            # Normalize to: timestamp, open, high, low, close, volume, quote_volume, quote_volume_repeat
            if df.shape[1] >= 8:
                df = df.iloc[:, :8]
                df.columns = ["timestamp", "open", "high", "low", "close", "volume","quote_volume","quote_volume_repeat"]
            else:
                return None

            # convert types reliably
            df = df.dropna()
            df["open"] = pd.to_numeric(df["open"], errors="coerce")
            df["high"] = pd.to_numeric(df["high"], errors="coerce")
            df["low"] = pd.to_numeric(df["low"], errors="coerce")
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            df["quote_volume"] = pd.to_numeric(df["quote_volume"], errors="coerce")
            df["quote_volume_repeat"] = pd.to_numeric(df["quote_volume_repeat"], errors="coerce")
            
            # timestamps from API might be in ms or seconds or strings — try to coerce
            try:
                df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms", utc=True)
            except Exception:
                try:
                    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="s", utc=True)
                except Exception:
                    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

            df.set_index("timestamp", inplace=True)
            df = df.sort_index()
            return df
        else:
            return None
    except Exception as e:
        return None

# 🎯 TP / SL hesaplama
def get_tp_and_sl(df : pd.DataFrame, signal : str, tp_percent: float = 0.5, sl_percent: float = 0.3) -> Union[Tuple[float, float], None]:
    if df is None or len(df) == 0:
        return None, None
    close = df["close"].iloc[-1]
    tp = sl = None

    if "LONG" in signal:
        tp = close * (1 + tp_percent / 100)
        sl = close * (1 - sl_percent / 100)
    elif "SHORT" in signal:
        tp = close * (1 - tp_percent / 100)
        sl = close * (1 + sl_percent / 100)

    return round(tp, 5) if tp else None, round(sl, 5) if sl else None

# 📈 Grafik çizme (TP/SL dahil)
async def get_chart(df : pd.DataFrame, strategy_name: str = "", granularity: GranularityType = "15min", tp: Union[float, None] = None, sl: Union[float, None] = None, symbol: str = "COIN") -> str:
    path = f"temp/{strategy_name}_{symbol}_{granularity}_chart.png"
    add_lines = []
    if tp:
        add_lines.append(
            mpf.make_addplot([tp] * len(df), color="green", linestyle="--")
        )
    if sl:
        add_lines.append(
            mpf.make_addplot([sl] * len(df), color="red", linestyle="--")
        )

    mpf.plot(
        df,
        type="candle",
        style="charles",
        volume=True,
        addplot=add_lines,
        savefig=path,
        ylim=(df["low"].min() * 0.99, df["high"].max() * 1.01),
    )
    return path
