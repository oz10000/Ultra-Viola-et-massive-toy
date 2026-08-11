# config.py
import os
import pytz
from datetime import timedelta

# ============================================================
# VERSIÓN
# ============================================================
VERSION = "12.0.0"
PROJECT_NAME = "🧸 JUNK TOYS Ω — Clasificación 25 Activos"

# ============================================================
# DATOS Y TIMEFRAMES
# ============================================================
TIMEFRAME = '5m'
TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d']
PRIMARY_TF = '5m'
LOOKBACK_DAYS = 365
INITIAL_CAPITAL = 10000.0
COMMISSION = 0.0004
SLIPPAGE = 0.0005
TIMEZONE = pytz.timezone('America/Argentina/Buenos_Aires')

# ============================================================
# EXCHANGES — IGUAL QUE EN JUNKTOYS
# ============================================================
EXCHANGES = {
    'okx': {'type': 'swap', 'enabled': True},
    'kucoin': {'type': 'linear', 'enabled': True},
    'mexc': {'type': 'swap', 'enabled': True},
    'kraken': {'type': 'spot', 'enabled': True},
    'binance': {'type': 'spot', 'enabled': True},
    'bybit': {'type': 'linear', 'enabled': True},
}
EXCHANGE_PRIORITY = ['okx', 'kucoin', 'mexc', 'kraken', 'binance', 'bybit']
EXCHANGE_CONFIGS = {
    'okx': {'type': 'swap', 'symbol_format': '{base}-{quote}-SWAP'},
    'kucoin': {'type': 'linear', 'symbol_format': '{base}{quote}M'},
    'mexc': {'type': 'swap', 'symbol_format': '{base}_{quote}'},
    'kraken': {'type': 'spot', 'symbol_format': '{base}/{quote}'},
    'binance': {'type': 'spot', 'symbol_format': '{base}/{quote}'},
    'bybit': {'type': 'linear', 'symbol_format': '{base}/{quote}'},
}

# ============================================================
# UNIVERSO DE 25 ACTIVOS (compatible con OKX)
# ============================================================
UNIVERSE = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT',
    'ADA/USDT', 'DOT/USDT', 'LINK/USDT', 'AVAX/USDT',
    'UNI/USDT', 'ATOM/USDT', 'NEAR/USDT', 'APT/USDT',
    'ARB/USDT', 'OP/USDT', 'INJ/USDT', 'SEI/USDT',
    'SUI/USDT', 'APE/USDT', 'FTM/USDT', 'ALGO/USDT',
    'ETC/USDT', 'LTC/USDT', 'DOGE/USDT'
]

FALLBACK_SYMBOLS = UNIVERSE  # Para compatibilidad

# ============================================================
# DIRECTORIOS DE CACHÉ
# ============================================================
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ROOT_DIR, 'data', 'cache')
OHLCV_DIR = os.path.join(ROOT_DIR, 'data', 'ohlcv')
RESULTS_DIR = os.path.join(ROOT_DIR, 'data', 'results')
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(OHLCV_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# ============================================================
# PARÁMETROS POR DEFECTO (igual que junktoys)
# ============================================================
DEFAULT_PARAMS = {
    'min_score': 0.30,
    'adx_threshold': 22,
    'ker_threshold': 0.42,
    'tp_mult': 2.5,
    'sl_mult': 1.0,
    'trailing_distance': 0.008,
    'trailing_activation': 0.012,
    'trailing_callback': 0.003,
    'break_even_trigger': 0.008,
    'break_even_buffer': 0.002,
    'max_hold_minutes': 120,
}

# ============================================================
# UMBRALES FIRM SIGNALS (para la señal aprobada)
# ============================================================
FIRM_EDGE_THRESHOLD = 0.45
FIRM_PIDELTA_THRESHOLD = 0.35
FIRM_CONSENSUS_THRESHOLD = 0.50
FIRM_REGIMES = ['Tendencia', 'Expansión']