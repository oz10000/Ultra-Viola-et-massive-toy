# signal_engine.py
import pandas as pd
import numpy as np
from core_engine import compute_adx, compute_ker, compute_atr, compute_regime, compute_pidelta_score


class Signal:
    def __init__(self, symbol, df, params):
        self.symbol = symbol
        self.params = params
        self.df = df

        # Campos de la señal
        self.score = 0.0
        self.adx = 0.0
        self.ker = 0.0
        self.atr_pct = 0.0
        self.regime = 'Chop'
        self.is_valid = False
        self.reason = "No evaluado"
        self.direction = None
        self.confidence = 0.0
        self.entry_price = 0.0
        self.sl_price = 0.0
        self.tp_price = 0.0
        self.trailing_activation = 0.0
        self.trailing_distance = 0.0
        self.break_even_trigger = 0.0
        self.break_even_buffer = 0.0
        self.max_hold_minutes = 0

        # Distancia a aprobación Firm
        self.distance_to_firm = 0.0
        self.is_firm = False

        if not df.empty and len(df) > 30:
            self._compute()

    def _compute(self):
        p = self.params
        close = self.df['close'].iloc[-1]

        # Calcular indicadores
        self.score = compute_pidelta_score(self.df)
        adx_series = compute_adx(self.df)
        self.adx = adx_series.iloc[-1] if not adx_series.empty else 0
        ker_series = compute_ker(self.df, 10)
        self.ker = ker_series.iloc[-1] if not ker_series.empty else 0
        atr_series = compute_atr(self.df)
        atr_val = atr_series.iloc[-1] if not atr_series.empty else 0
        self.atr_pct = atr_val / close if close > 0 else 0
        self.regime = compute_regime(self.df)

        # Verificar validez (filtros del sistema original)
        self.is_valid = True
        self.reason = "OK"

        if abs(self.score) < p['min_score']:
            self.is_valid = False
            self.reason = f"score {self.score:.2f} < {p['min_score']}"
        elif self.adx < p['adx_threshold']:
            self.is_valid = False
            self.reason = f"ADX {self.adx:.1f} < {p['adx_threshold']}"
        elif self.ker < p['ker_threshold']:
            self.is_valid = False
            self.reason = f"KER {self.ker:.2f} < {p['ker_threshold']}"
        elif self.regime == 'Chop':
            self.is_valid = False
            self.reason = "Régimen Chop"

        if self.is_valid:
            self.direction = 'LONG' if self.score > 0 else 'SHORT'
            self.entry_price = close

            # SL y TP
            sl_mult = p['sl_mult']
            tp_mult = p['tp_mult']
            if self.regime in ['Tendencia Fuerte', 'Expansión']:
                tp_mult *= 1.1

            if self.direction == 'LONG':
                self.sl_price = close * (1 - sl_mult * self.atr_pct)
                self.tp_price = close * (1 + tp_mult * self.atr_pct)
            else:
                self.sl_price = close * (1 + sl_mult * self.atr_pct)
                self.tp_price = close * (1 - tp_mult * self.atr_pct)

            # Trailing Stop
            self.trailing_activation = p['trailing_activation']
            self.trailing_distance = p['trailing_distance']
            self.break_even_trigger = p['break_even_trigger']
            self.break_even_buffer = p['break_even_buffer']
            self.max_hold_minutes = p['max_hold_minutes']

            # Confianza
            self.confidence = 0.3 + 0.3 * (self.adx / 40) + 0.2 * self.ker + 0.2 * abs(self.score)
            self.confidence = min(1.0, self.confidence)

        # ===== FIRM SIGNALS — distancia a aprobación =====
        from config import FIRM_EDGE_THRESHOLD, FIRM_PIDELTA_THRESHOLD, FIRM_CONSENSUS_THRESHOLD, FIRM_REGIMES

        edge = self.score  # Usamos el score como proxy del edge
        pidelta = self.score
        consensus = self.adx / 40  # Proxy de consenso
        regime_ok = self.regime in FIRM_REGIMES

        # Distancia a aprobación (0 = aprobado, 1 = lejos)
        dist = 0.0
        if FIRM_EDGE_THRESHOLD > abs(edge):
            dist += (FIRM_EDGE_THRESHOLD - abs(edge)) / FIRM_EDGE_THRESHOLD
        if FIRM_PIDELTA_THRESHOLD > abs(pidelta):
            dist += (FIRM_PIDELTA_THRESHOLD - abs(pidelta)) / FIRM_PIDELTA_THRESHOLD
        if FIRM_CONSENSUS_THRESHOLD > abs(consensus):
            dist += (FIRM_CONSENSUS_THRESHOLD - abs(consensus)) / FIRM_CONSENSUS_THRESHOLD
        if not regime_ok:
            dist += 0.3

        self.distance_to_firm = min(1.0, dist)
        self.is_firm = (
            abs(edge) >= FIRM_EDGE_THRESHOLD and
            abs(pidelta) >= FIRM_PIDELTA_THRESHOLD and
            abs(consensus) >= FIRM_CONSENSUS_THRESHOLD and
            regime_ok
        )

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'score': round(self.score, 4),
            'adx': round(self.adx, 1),
            'ker': round(self.ker, 3),
            'atr_pct': round(self.atr_pct, 4),
            'regime': self.regime,
            'is_valid': self.is_valid,
            'reason': self.reason,
            'direction': self.direction,
            'confidence': round(self.confidence, 3),
            'entry_price': round(self.entry_price, 4),
            'sl_price': round(self.sl_price, 4),
            'tp_price': round(self.tp_price, 4),
            'trailing_activation': self.trailing_activation,
            'trailing_distance': self.trailing_distance,
            'break_even_trigger': self.break_even_trigger,
            'max_hold_minutes': self.max_hold_minutes,
            'distance_to_firm': round(self.distance_to_firm, 3),
            'is_firm': self.is_firm,
        }
