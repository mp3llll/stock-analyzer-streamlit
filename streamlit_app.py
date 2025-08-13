import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

# הגדרת עמוד
st.set_page_config(
    page_title="ניתוח מניות מתקדם",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS מותאם אישית
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
    font-weight: bold;
}
.metric-card {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 10px;
    border-left: 5px solid #1f77b4;
    margin: 0.5rem 0;
}
.positive {
    color: #00cc96;
    font-weight: bold;
}
.negative {
    color: #ef553b;
    font-weight: bold;
}
.neutral {
    color: #ffa15a;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

class StockAnalyzer:
    def __init__(self, symbol):
        self.symbol = symbol
        self.stock = yf.Ticker(symbol)
        self.sp500 = yf.Ticker("^GSPC")
        self.get_data()
    
    def get_data(self):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        try:
            self.stock_data = self.stock.history(start=start_date)
            self.sp500_data = self.sp500.history(start=start_date)
            if self.stock_data.empty:
                raise ValueError("No data found for symbol")
        except Exception as e:
            raise ValueError(f"Error fetching data: {str(e)}")

    def calculate_performance_metrics(self):
        df = self.stock_data.copy()
        current_price = df['Close'].iloc[-1]
        
        metrics = {}
        periods = {
            '1_week': 5,
            '1_month': 22,
            '3_months': 66,
            '6_months': 126,
            '1_year': 252
        }
        
        for period_name, days in periods.items():
            if len(df) >= days:
                start_price = df['Close'].iloc[-days]
                performance = (current_price - start_price) / start_price * 100
                metrics[period_name] = performance
            else:
                metrics[period_name] = None
                
        return metrics

    def calculate_trend_indicators(self):
        df = self.stock_data.tail(20).copy()
        
        df['green_candle'] = df['Close'] > df['Open']
        green_candles = df['green_candle'].sum()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        df_full = self.stock_data.copy()
        ma20 = df_full['Close'].rolling(window=20).mean()
        ma50 = df_full['Close'].rolling(window=50).mean()
        ma150 = df_full['Close'].rolling(window=150).mean()
        
        current_price = df_full['Close'].iloc[-1]
        
        return {
            'green_candles_last_20': int(green_candles),
            'current_rsi': float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0,
            'above_ma20': bool(current_price > ma20.iloc[-1]) if not pd.isna(ma20.iloc[-1]) else False,
            'above_ma50': bool(current_price > ma50.iloc[-1]) if not pd.isna(ma50.iloc[-1]) else False,
            'above_ma150': bool(current_price > ma150.iloc[-1]) if not pd.isna(ma150.iloc[-1]) else False,
        }

    def calculate_higher_lows_highs(self):
        df = self.stock_data.copy()
        
        if len(df) >= 120:
            start_price = df['Close'].iloc[-120]
            current_price = df['Close'].iloc[-1]
            six_month_return = (current_price - start_price) / start_price
            
            if six_month_return > 0.20:
                return True
                
        if len(df) >= 60:
            start_price = df['Close'].iloc[-60]
            current_price = df['Close'].iloc[-1]
            three_month_return = (current_price - start_price) / start_price
            
            if three_month_return > 0.15:
                return True
        
        return False

    def analyze(self):
        try:
            current_price = self.stock_data['Close'].iloc[-1]
            performance_metrics = self.calculate_performance_metrics()
            trend_indicators = self.calculate_trend_indicators()
            uptrend = self.calculate_higher_lows_highs()
            
            info = self.stock.info
            
            entry_score = 0
            reasons = []
            risks = []

            if performance_metrics.get('6_months') and performance_metrics['6_months'] > 50:
                entry_score += 2
                reasons.append(f"ביצועים יוצאי דופן בחצי שנה: {performance_metrics['6_months']:.1f}%")
            elif performance_metrics.get('6_months') and performance_metrics['6_months'] > 25:
                entry_score += 1
                reasons.append(f"ביצועים מצוינים בחצי שנה: {performance_metrics['6_months']:.1f}%")

            if uptrend:
                entry_score += 2
                reasons.append("מגמה עולה חזקה")
            else:
                risks.append("אין מגמה עולה ברורה")

            moving_averages_above = sum([
                trend_indicators['above_ma20'],
                trend_indicators['above_ma50'],
                trend_indicators['above_ma150']
            ])

            if moving_averages_above == 3:
                entry_score += 2
                reasons.append("מחיר מעל כל הממוצעים הנעים")
            elif moving_averages_above == 2:
                entry_score += 1
                reasons.append("מחיר מעל רוב הממוצעים הנעים")
            else:
                risks.append("מחיר מתחת לרוב הממוצעים הנעים")

            rsi = trend_indicators['current_rsi']
            if 40 <= rsi <= 60:
                entry_score += 1
                reasons.append(f"RSI אופטימלי: {rsi:.1f}")
            elif rsi > 70:
                risks.append(f"RSI גבוה מדי: {rsi:.1f}")
            elif rsi < 30:
                risks.append(f"RSI נמוך מדי: {rsi:.1f}")

            return {
                'symbol': self.symbol,
                'current_price': float(current_price),
                'entry_score': float(entry_score),
                'max_score': 8.0,
                'supporting_factors': reasons,
                'risk_factors': risks,
                'performance': performance_metrics,
                'trend': {
                    'uptrend': uptrend,
                },
                'technical_indicators': trend_indicators,
                'company_info': {
                    'market_cap': info.get('marketCap', 0),
                    'sector': info.get('sector', 'Unknown'),
                    'shortName': info.get('shortName', self.symbol)
                }
            }
        except Exception as e:
            raise ValueError(f"Error in analysis: {str(e)}")

# כותרת ראשית
st.markdown('<h1 class="main-header">📈 ניתוח מניות מתקדם</h1>', unsafe_allow_html=True)

# סיידבר
with st.sidebar:
    st.header("🔍 חיפוש מניה")
    symbol = st.text_input("הכנס סימול מניה:", value="AAPL", placeholder="AAPL, MSFT, GOOGL...")
    analyze_button = st.button("🚀 נתח מניה", type="primary")
    
    st.markdown("---")
    st.markdown("**דוגמאות פופולריות:**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("AAPL"):
            symbol = "AAPL"
            analyze_button = True
        if st.button("MSFT"):
            symbol = "MSFT"
            analyze_button = True
        if st.button("GOOGL"):
            symbol = "GOOGL"
            analyze_button = True
    with col2:
        if st.button("TSLA"):
            symbol = "TSLA"
            analyze_button = True
        if st.button("AMZN"):
            symbol = "AMZN"
            analyze_button = True
        if st.button("NVDA"):
            symbol = "NVDA"
            analyze_button = True

if analyze_button and symbol:
    try:
        with st.spinner(f'מנתח את {symbol.upper()}... אנא המתן'):
            analyzer = StockAnalyzer(symbol.upper())
            analysis = analyzer.analyze()
            
        # כותרת המניה
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.title(f"{analysis['company_info']['shortName']} ({analysis['symbol']})")
            st.subheader(f"💼 {analysis['company_info']['sector']}")
        
        with col2:
            st.metric("מחיר נוכחי", f"${analysis['current_price']:.2f}")
        
        with col3:
            score_percentage = (analysis['entry_score'] / analysis['max_score']) * 100
            color = "🟢" if score_percentage >= 75 else "🟡" if score_percentage >= 50 else "🔴"
            st.metric("ציון כניסה", f"{color} {score_percentage:.1f}%")

        # ביצועים היסטוריים
        st.header("📊 ביצועים היסטוריים")
        
        perf_cols = st.columns(5)
        periods = [
            ("שבוע", "1_week"),
            ("חודש", "1_month"), 
            ("3 חודשים", "3_months"),
            ("6 חודשים", "6_months"),
            ("שנה", "1_year")
        ]
        
        for i, (period_name, period_key) in enumerate(periods):
            with perf_cols[i]:
                if analysis['performance'][period_key] is not None:
                    value = analysis['performance'][period_key]
                    delta_color = "normal" if value >= 0 else "inverse"
                    st.metric(
                        period_name,
                        f"{value:+.1f}%",
                        delta=f"{value:+.1f}%",
                        delta_color=delta_color
                    )
                else:
                    st.metric(period_name, "לא זמין")

        # גרף מחירים
        st.header("📈 גרף מחירים")
        
        # יצירת גרף candlestick
        fig = go.Figure(data=go.Candlestick(
            x=analyzer.stock_data.index,
            open=analyzer.stock_data['Open'],
            high=analyzer.stock_data['High'],
            low=analyzer.stock_data['Low'],
            close=analyzer.stock_data['Close'],
            name=analysis['symbol']
        ))
        
        fig.update_layout(
            title=f"גרף מחירים - {analysis['symbol']}",
            yaxis_title="מחיר ($)",
            xaxis_title="תאריך",
            height=500,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # נתונים טכניים
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("📊 אינדיקטורים טכניים")
            
            indicators = [
                ("נרות ירוקים (20 ימים)", analysis['technical_indicators']['green_candles']),
                ("RSI", f"{analysis['technical_indicators']['rsi']:.1f}"),
                ("מעל ממוצע 20", "✅" if analysis['technical_indicators']['above_ma20'] else "❌"),
                ("מעל ממוצע 50", "✅" if analysis['technical_indicators']['above_ma50'] else "❌"),
                ("מעל ממוצע 150", "✅" if analysis['technical_indicators']['above_ma150'] else "❌"),
            ]
            
            for label, value in indicators:
                st.markdown(f"**{label}:** {value}")

        with col2:
            st.header("💼 פרטי החברה")
            
            market_cap = analysis['company_info']['market_cap']
            if market_cap > 0:
                if market_cap >= 1e12:
                    market_cap_str = f"${market_cap/1e12:.2f}T"
                elif market_cap >= 1e9:
                    market_cap_str = f"${market_cap/1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap/1e6:.2f}M"
                else:
                    market_cap_str = f"${market_cap:,.0f}"
            else:
                market_cap_str = "לא זמין"
            
            st.markdown(f"**שווי שוק:** {market_cap_str}")
            st.markdown(f"**ענף:** {analysis['company_info']['sector']}")
            st.markdown(f"**מגמה כללית:** {'עולה ✅' if analysis['trend']['uptrend'] else 'לא עולה ❌'}")

        # גורמים תומכים וסיכונים
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("✅ גורמים תומכים")
            for factor in analysis['supporting_factors']:
                st.success(f"• {factor}")
                
        with col2:
            st.header("⚠️ גורמי סיכון")
            for risk in analysis['risk_factors']:
                st.warning(f"• {risk}")

        # המלצה סופית
        st.header("🎯 המלצה סופית")
        
        if score_percentage >= 75:
            st.success("🟢 **המלצה: כניסה אידיאלית** - כל הקריטריונים מצביעים על הזדמנות מצוינת")
        elif score_percentage >= 50:
            st.warning("🟡 **המלצה: כניסה אפשרית עם זהירות** - יש פוטנציאל אבל גם סיכונים")
        else:
            st.error("🔴 **המלצה: לא מומלץ להיכנס כרגע** - יותר מדי סיכונים")

    except Exception as e:
        st.error(f"❌ שגיאה בניתוח המניה: {str(e)}")
        st.info("💡 וודא שהסימול נכון (לדוגמה: AAPL, MSFT, GOOGL)")

else:
    # עמוד ברירת מחדל
    st.info("👈 הכנס סימול מניה בצד שמאל כדי להתחיל בניתוח")
    
    # דוגמאות
    st.header("🌟 דוגמאות פופולריות")
    
    examples = [
        ("AAPL", "Apple Inc.", "Technology"),
        ("MSFT", "Microsoft", "Technology"), 
        ("GOOGL", "Alphabet", "Technology"),
        ("TSLA", "Tesla", "Consumer Cyclical"),
        ("AMZN", "Amazon", "Consumer Cyclical"),
        ("NVDA", "NVIDIA", "Technology")
    ]
    
    cols = st.columns(3)
    for i, (symbol, name, sector) in enumerate(examples):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="metric-card">
                <h4>{symbol}</h4>
                <p><strong>{name}</strong></p>
                <p>{sector}</p>
            </div>
            """, unsafe_allow_html=True)

# פוטר
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🚀 ניתוח מניות מתקדם | פותח בעברית עם ❤️</p>
        <p>⚠️ זהירות: המידע כאן הוא לצרכי מידע בלבד ולא מהווה עצה השקעתית</p>
    </div>
    """, 
    unsafe_allow_html=True
)