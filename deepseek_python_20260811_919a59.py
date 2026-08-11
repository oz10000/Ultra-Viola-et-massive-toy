# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import logging

from data_engine import DataEngine
from config import (
    INITIAL_CAPITAL, DEFAULT_PARAMS, VERSION, PROJECT_NAME,
    TIMEFRAME, UNIVERSE, FALLBACK_SYMBOLS, EXCHANGES
)
from signal_engine import Signal
from core_engine import compute_atr, compute_adx, compute_ker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=f"{PROJECT_NAME}",
    page_icon="🧸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# TÍTULO
# ============================================================
st.title(f"{PROJECT_NAME}")
st.subheader(f"v{VERSION} — Clasificación de 25 activos · Señal Firm incluida")
st.markdown("---")

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/emoji/96/000000/teddy-bear-emoji.png", width=80)
    st.header("⚙️ Configuración")
    st.caption(f"Capital: ${INITIAL_CAPITAL:,.2f}")
    st.caption(f"Timeframe: {TIMEFRAME}")
    st.caption(f"Activos: {len(UNIVERSE)}")

    st.markdown("---")
    st.header("🎯 Acciones")
    refresh_btn = st.button("🔄 Actualizar Ranking", type="primary", use_container_width=True)

    st.markdown("---")
    st.header("📊 Estado")
    st.caption(f"Última actualización: {st.session_state.get('last_refresh', 'Nunca')}")
    st.caption(f"Señales válidas: {len(st.session_state.get('valid_signals', []))}")
    st.caption(f"Señales Firm: {len([s for s in st.session_state.get('valid_signals', []) if s.get('is_firm', False)])}")

# ============================================================
# INICIALIZACIÓN
# ============================================================
if 'data_engine' not in st.session_state:
    with st.spinner("🔄 Inicializando motor de datos..."):
        st.session_state.data_engine = DataEngine()
        st.session_state.certified_symbols = st.session_state.data_engine.get_certified_assets(UNIVERSE)
        if not st.session_state.certified_symbols:
            st.session_state.certified_symbols = FALLBACK_SYMBOLS[:25]
        st.session_state.symbols = st.session_state.certified_symbols
        st.session_state.data_dict = {}
        st.session_state.signals = []
        st.session_state.valid_signals = []
        st.session_state.last_refresh = None

# ============================================================
# FUNCIONES
# ============================================================
def refresh_ranking():
    """Escanea todos los activos y genera el ranking completo."""
    de = st.session_state.data_engine
    symbols = st.session_state.symbols[:25]
    signals = []
    data_dict = {}

    with st.spinner(f"🔍 Escaneando {len(symbols)} activos..."):
        for sym in symbols:
            df = de.fetch_ohlcv(sym, limit=300)
            if df is not None and not df.empty:
                data_dict[sym] = df
                s = Signal(sym, df, DEFAULT_PARAMS)
                signals.append(s.to_dict())

    st.session_state.data_dict = data_dict
    st.session_state.signals = signals
    st.session_state.valid_signals = [s for s in signals if s.get('is_valid', False)]
    st.session_state.last_refresh = datetime.now().strftime("%H:%M:%S")

    # Ordenar por score (mejores LONG y SHORT)
    longs = sorted([s for s in signals if s.get('direction') == 'LONG'], key=lambda x: x.get('score', 0), reverse=True)
    shorts = sorted([s for s in signals if s.get('direction') == 'SHORT'], key=lambda x: x.get('score', 0), reverse=True)

    st.session_state.top_long = longs[:5]
    st.session_state.top_short = shorts[:5]

    logger.info(f"✅ Escaneo completado: {len(signals)} señales, {len(st.session_state.valid_signals)} válidas")

# Ejecutar al inicio si no hay datos
if 'signals' not in st.session_state or not st.session_state.signals:
    refresh_ranking()

if refresh_btn:
    refresh_ranking()
    st.rerun()

# ============================================================
# RANKING COMPLETO (TODOS LOS ACTIVOS)
# ============================================================
st.header("📊 Ranking Completo — 25 Activos")

signals = st.session_state.signals
if signals:
    df_all = pd.DataFrame(signals)

    # Columnas a mostrar
    cols_to_show = [
        'symbol', 'direction', 'score', 'adx', 'ker', 'atr_pct',
        'regime', 'is_valid', 'reason', 'confidence',
        'entry_price', 'sl_price', 'tp_price',
        'distance_to_firm', 'is_firm'
    ]
    available_cols = [c for c in cols_to_show if c in df_all.columns]
    df_display = df_all[available_cols].copy()

    # Formato
    format_dict = {
        'score': '{:.3f}',
        'adx': '{:.1f}',
        'ker': '{:.3f}',
        'atr_pct': '{:.2%}',
        'confidence': '{:.1%}',
        'entry_price': '${:.4f}',
        'sl_price': '${:.4f}',
        'tp_price': '${:.4f}',
        'distance_to_firm': '{:.1%}',
    }
    st.dataframe(
        df_display.style.format(format_dict),
        use_container_width=True,
        height=600
    )

    # Resumen
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total señales", len(signals))
    col2.metric("Señales válidas", len(st.session_state.valid_signals))
    col3.metric("Señales Firm", len([s for s in signals if s.get('is_firm', False)]))
    col4.metric("Activos", len(df_all['symbol'].unique()))

else:
    st.info("No hay datos. Presiona 'Actualizar Ranking'.")

# ============================================================
# TOP 5 LONG
# ============================================================
st.header("🏆 TOP 5 LONG")
top_long = st.session_state.get('top_long', [])
if top_long:
    df_long = pd.DataFrame(top_long)
    cols_show = ['symbol', 'score', 'adx', 'ker', 'regime', 'confidence', 'is_valid', 'is_firm', 'distance_to_firm']
    available = [c for c in cols_show if c in df_long.columns]
    st.dataframe(
        df_long[available].style.format({
            'score': '{:.3f}',
            'adx': '{:.1f}',
            'ker': '{:.3f}',
            'confidence': '{:.1%}',
            'distance_to_firm': '{:.1%}',
        }),
        use_container_width=True
    )
else:
    st.info("No hay señales LONG.")

# ============================================================
# TOP 5 SHORT
# ============================================================
st.header("⬇️ TOP 5 SHORT")
top_short = st.session_state.get('top_short', [])
if top_short:
    df_short = pd.DataFrame(top_short)
    cols_show = ['symbol', 'score', 'adx', 'ker', 'regime', 'confidence', 'is_valid', 'is_firm', 'distance_to_firm']
    available = [c for c in cols_show if c in df_short.columns]
    st.dataframe(
        df_short[available].style.format({
            'score': '{:.3f}',
            'adx': '{:.1f}',
            'ker': '{:.3f}',
            'confidence': '{:.1%}',
            'distance_to_firm': '{:.1%}',
        }),
        use_container_width=True
    )
else:
    st.info("No hay señales SHORT.")

# ============================================================
# DISTRIBUCIÓN
# ============================================================
st.header("📈 Distribución de Señales")

if signals:
    df_dist = pd.DataFrame(signals)

    col1, col2 = st.columns(2)

    with col1:
        # Dirección
        dir_counts = df_dist['direction'].value_counts()
        fig1 = px.pie(values=dir_counts.values, names=dir_counts.index, title="Dirección")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Régimen
        regime_counts = df_dist['regime'].value_counts()
        fig2 = px.bar(x=regime_counts.index, y=regime_counts.values, title="Régimen de mercado")
        st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# PIE DE PÁGINA
# ============================================================
st.markdown("---")
st.caption(f"🧸 JUNK TOYS Ω — v{VERSION} · {len(UNIVERSE)} activos · Última actualización: {st.session_state.get('last_refresh', 'Nunca')}")