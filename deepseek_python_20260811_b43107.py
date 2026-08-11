# core_engine.py
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def compute_adx(df, period=14):
    """ADX (Average Directional Index) con validación de NaN."""
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)

    high, low, close = df['high'], df['low'], df['close']

    plus_dm = high.diff()
    minus_dm = low.diff().abs() * -1
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = minus_dm.abs()

    tr = pd.DataFrame({
        'hl': high - low,
        'hc': (high - close.shift()).abs(),
        'lc': (low - close.shift()).abs()
    }).max(axis=1)

    atr = tr.rolling(period).mean()
    atr = atr.replace(0, np.nan)

    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(period).mean()
    adx = adx.fillna(0).replace([np.inf, -np.inf], 0)

    return adx


def compute_ker(df, period=10):
    """KER (Kaufman Efficiency Ratio) con validación."""
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)

    close = df['close']
    change = abs(close.diff(period))
    volatility = close.diff().abs().rolling(period).sum()
    ker = change / (volatility + 1e-9)
    ker = ker.fillna(0).replace([np.inf, -np.inf], 0)

    return ker


def compute_atr(df, period=14):
    """ATR (Average True Range) con validación."""
    if df.empty or len(df) < period:
        return pd.Series(0.0, index=df.index)

    high, low, close = df['high'], df['low'], df['close']

    tr = pd.DataFrame({
        'hl': high - low,
        'hc': (high - close.shift()).abs(),
        'lc': (low - close.shift()).abs()
    }).max(axis=1)

    atr = tr.rolling(period).mean()
    atr = atr.fillna(0).replace([np.inf, -np.inf], 0)

    return atr


def compute_regime(df, atr_period=14):
    """Clasifica régimen: 'Tendencia Fuerte', 'Tendencia', 'Chop', 'Expansión'."""
    if df.empty or len(df) < 30:
        return 'Chop'

    close = df['close']
    adx_series = compute_adx(df)
    atr_series = compute_atr(df, atr_period)

    adx_val = adx_series.iloc[-1] if not adx_series.empty else 0
    atr_pct = atr_series.iloc[-1] / close.iloc[-1] if close.iloc[-1] > 0 else 0

    if adx_val > 40 and atr_pct > 0.02:
        return 'Expansión'
    elif adx_val > 30:
        return 'Tendencia Fuerte'
    elif adx_val > 20:
        return 'Tendencia'
    else:
        return 'Chop'


def compute_pidelta_score(df, ema_period=22, atr_period=14):
    """
    Score compuesto [-1, 1].
    Incluye: Trend (25%), Strength (ADX/40)(20%), KER(15%), ATR rel(10%), Momentum(10%).
    """
    if df.empty or len(df) < 30:
        return 0.0

    close = df['close']
    high = df['high']
    low = df['low']

    # EMA y MACD
    ema9 = close.ewm(span=9).mean()
    ema21 = close.ewm(span=21).mean()
    macd = ema9 - ema21
    signal = macd.ewm(span=9).mean()
    hist = macd - signal

    # Componentes
    trend = np.clip((close.iloc[-1] / close.iloc[-21] - 1) * 10, -1, 1) if len(close) >= 21 else 0

    adx_series = compute_adx(df)
    adx_val = adx_series.iloc[-1] if not adx_series.empty else 0
    strength = np.clip(adx_val / 40, 0, 1)

    ker_series = compute_ker(df)
    ker_val = ker_series.iloc[-1] if not ker_series.empty else 0
    ker_score = np.clip(ker_val, 0, 1)

    atr_series = compute_atr(df, atr_period)
    atr_val = atr_series.iloc[-1] if not atr_series.empty else 0
    atr_rel = np.clip(atr_val / close.iloc[-1] * 50, 0, 1) if close.iloc[-1] > 0 else 0

    momentum = np.clip(hist.iloc[-1] / (atr_val + 1e-9), -1, 1) if len(hist) > 0 else 0

    # Pesos
    score = (
        0.25 * trend +
        0.20 * strength +
        0.15 * ker_score +
        0.10 * atr_rel +
        0.10 * momentum
    )
    score = np.clip(score, -1, 1)

    return score