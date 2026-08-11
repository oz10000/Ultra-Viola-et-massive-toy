# data_engine.py
import ccxt
import pandas as pd
import numpy as np
import os
import time
import pickle
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from config import (
    EXCHANGE_PRIORITY, EXCHANGE_CONFIGS, FALLBACK_SYMBOLS,
    CACHE_DIR, OHLCV_DIR, TIMEFRAME, LOOKBACK_DAYS
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataEngine:
    """Motor de datos con caché, validación de integridad y certificación de activos."""

    def __init__(self, exchanges=None):
        os.makedirs(OHLCV_DIR, exist_ok=True)
        os.makedirs(CACHE_DIR, exist_ok=True)

        self.exchanges = {}
        self.exchange_status = {}
        self.symbol_maps = {}

        if exchanges is None:
            exchanges = EXCHANGE_PRIORITY

        for ex_id in exchanges:
            self._connect_exchange(ex_id)

        self.primary = self._get_primary_exchange()
        self._cache = {}
        self._cache_timestamps = {}
        self._universe_cache = None
        self._universe_by_exchange = {}
        self._certified_assets = None
        self._certified_assets_timestamp = None

        logger.info(f"✅ DataEngine listo. Primary: {self.primary}")

    def _connect_exchange(self, ex_id):
        for attempt in range(3):
            try:
                ex_class = getattr(ccxt, ex_id)
                options = {'enableRateLimit': True}
                if ex_id == 'binance':
                    options['options'] = {'defaultType': 'spot'}
                elif ex_id == 'bybit':
                    options['options'] = {'defaultType': 'linear'}
                elif ex_id == 'okx':
                    options['options'] = {'defaultType': 'swap'}
                elif ex_id == 'mexc':
                    options['options'] = {'defaultType': 'swap'}
                elif ex_id == 'kucoin':
                    options['options'] = {'defaultType': 'linear'}
                elif ex_id == 'kraken':
                    options['options'] = {'defaultType': 'spot'}
                else:
                    options['options'] = {'defaultType': 'spot'}

                exchange = ex_class(options)
                exchange.load_markets()
                self.exchanges[ex_id] = exchange
                self.exchange_status[ex_id] = 'connected'
                self.symbol_maps[ex_id] = {m['symbol']: m for m in exchange.markets.values()}
                logger.info(f"✅ Conectado a {ex_id}")
                return
            except Exception as e:
                logger.warning(f"Intento {attempt+1}/3 para {ex_id} falló: {e}")
                time.sleep(2)

        self.exchanges[ex_id] = None
        self.exchange_status[ex_id] = 'failed'
        logger.error(f"❌ No se pudo conectar a {ex_id}")

    def _get_primary_exchange(self):
        for ex_id in EXCHANGE_PRIORITY:
            if self.exchanges.get(ex_id) is not None:
                return ex_id
        return None

    def get_available_exchanges(self):
        return [ex_id for ex_id, ex in self.exchanges.items() if ex is not None]

    def _get_cache_key(self, symbol, timeframe, limit):
        return hashlib.md5(f"{symbol}_{timeframe}_{limit}".encode()).hexdigest()

    def fetch_ohlcv(self, symbol: str, timeframe: str = TIMEFRAME, limit: int = 300) -> Optional[pd.DataFrame]:
        """Descarga velas con caché y fallback entre exchanges."""
        cache_key = self._get_cache_key(symbol, timeframe, limit)
        cache_file = os.path.join(OHLCV_DIR, f"{cache_key}.parquet")

        # Intentar cargar desde caché
        if os.path.exists(cache_file):
            try:
                df = pd.read_parquet(cache_file)
                # Verificar que los datos no estén obsoletos (> 1 hora)
                if (datetime.now() - pd.Timestamp(df.index[-1])).total_seconds() < 3600:
                    logger.debug(f"✅ Caché válido para {symbol}")
                    return df
                else:
                    logger.debug(f"⏳ Caché obsoleto para {symbol}, actualizando...")
            except Exception as e:
                logger.warning(f"⚠️ Error leyendo caché de {symbol}: {e}")

        # Descargar con fallback entre exchanges
        for ex_id in EXCHANGE_PRIORITY:
            exchange = self.exchanges.get(ex_id)
            if exchange is None:
                continue

            for attempt in range(3):
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                    if not ohlcv:
                        continue

                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    df.sort_index(inplace=True)

                    # Guardar en caché
                    try:
                        df.to_parquet(cache_file)
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo guardar caché de {symbol}: {e}")

                    logger.info(f"✅ Descargado {symbol} desde {ex_id} ({len(df)} velas)")
                    return df

                except ccxt.RateLimitExceeded:
                    wait = (attempt + 1) * 2
                    logger.warning(f"⏳ Rate limit en {ex_id} (intento {attempt+1}/3). Esperando {wait}s...")
                    time.sleep(wait)
                except ccxt.BadSymbol:
                    logger.warning(f"❌ Símbolo {symbol} no existe en {ex_id}")
                    break
                except Exception as e:
                    logger.error(f"❌ Error en {ex_id} (intento {attempt+1}/3): {e}")
                    time.sleep(1)

            logger.warning(f"⚠️ {ex_id} falló para {symbol}, probando siguiente exchange...")

        logger.error(f"❌ No se pudo descargar {symbol} después de todos los intentos")
        return None

    def get_certified_assets(self, symbols: Optional[List[str]] = None) -> List[str]:
        """Verifica qué símbolos existen en el exchange primario."""
        if symbols is None:
            symbols = FALLBACK_SYMBOLS

        certified = []
        exchange = self.exchanges.get(self.primary)
        if exchange is None:
            logger.error("❌ No hay exchange primario disponible")
            return certified[:10]

        markets = exchange.load_markets()
        for sym in symbols:
            if sym in markets:
                certified.append(sym)
                logger.debug(f"✅ Activo certificado: {sym}")
            else:
                logger.warning(f"⚠️ Activo no encontrado: {sym}")

        return certified[:25]

    def get_available_timeframes(self, exchange_id: Optional[str] = None) -> List[str]:
        if exchange_id is None:
            exchange_id = self.primary
        exchange = self.exchanges.get(exchange_id)
        if exchange is None:
            return TIMEFRAMES
        return list(exchange.timeframes.keys()) if hasattr(exchange, 'timeframes') else TIMEFRAMES