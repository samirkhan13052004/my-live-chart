import streamlit as st
from SmartApi import SmartConnect
import pyotp
import pandas as pd
import pandas_ta as ta
from streamlit_lightweight_charts import renderLightweightCharts
import time

# पेज की सेटिंग
st.set_page_config(layout="wide", page_title="My Custom Trading Platform")

# सेशन स्टेट में API ऑब्जेक्ट सुरक्षित रखना ताकि बार-बार लॉगिन न हो
if "smart_api" not in st.session_state:
    st.session_state.smart_api = None

# --- 1. साइडबार में सुरक्षित लॉगिन फॉर्म ---
st.sidebar.title("Angel One Login")
with st.sidebar.form("login_form"):
    api_key = st.text_input("API Key", type="password")
    client_code = st.text_input("Client Code")
    pin = st.text_input("MPIN", type="password")
    totp_secret = st.text_input("TOTP Secret Key", type="password")
    
    submit_btn = st.form_submit_button("Connect API")
    
    if submit_btn:
        if api_key and client_code and pin and totp_secret:
            try:
                # API लॉगिन लॉजिक
                smart_api = SmartConnect(api_key)
                totp_val = pyotp.TOTP(totp_secret).now()
                login_data = smart_api.generateSession(client_code, pin, totp_val)
                
                if login_data['status']:
                    st.session_state.smart_api = smart_api
                    st.sidebar.success("सफलतापूर्वक कनेक्ट हो गया!")
                else:
                    st.sidebar.error(f"लॉगिन विफल: {login_data['message']}")
            except Exception as e:
                st.sidebar.error(f"लॉगिन एरर: {e}")
        else:
            st.sidebar.warning("कृपया सभी क्रेडेंशियल्स भरें।")

# --- 2. मुख्य स्क्रीन (चार्ट और डेटा) ---
if st.session_state.smart_api:
    st.title("Live Nifty / BankNifty Chart")
    
    # यूजर से टोकन लेना (डिफ़ॉल्ट 3045 SBI का है, निफ्टी के लिए 99926000)
    col1, col2 = st.columns([1, 4])
    with col1:
        token = st.text_input("Symbol Token", value="3045")
        exchange = st.selectbox("Exchange", ["NSE", "NFO", "BSE"])
        interval = st.selectbox("Timeframe", ["ONE_MINUTE", "FIVE_MINUTE", "FIFTEEN_MINUTE"])

    try:
        # डेटा फेच करना
        hist_data = st.session_state.smart_api.getCandleData({
            "exchange": exchange,
            "symboltoken": token,
            "interval": interval,
            "fromdate": (pd.Timestamp.now() - pd.Timedelta(days=3)).strftime("%Y-%m-%d 09:15"),
            "todate": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        })

        if hist_data and hist_data.get('data'):
            # डेटा को Pandas DataFrame में बदलना
            df = pd.DataFrame(hist_data['data'], columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            df['time'] = pd.to_datetime(df['time']).astype('int64') // 10**9 + 19800  # IST Timezone
            
            # --- 3. आपका कस्टम इंडिकेटर (Pine Script लॉजिक यहाँ डालें) ---
            # उदाहरण: 20 Period EMA
            df['ema_20'] = ta.ema(df['close'], length=20)

            # चार्ट के लिए डेटा तैयार करना
            candles = df[['time', 'open', 'high', 'low', 'close']].to_dict('records')
            indicator_data = df[['time', 'ema_20']].dropna().rename(columns={'ema_20': 'value'}).to_dict('records')

            # --- 4. TradingView (Lightweight) चार्ट की डिज़ाइन ---
            chart_options = {
                "height": 550,
                "layout": {"background": {"color": "#131722"}, "textColor": "#d1d4dc"},
                "grid": {"vertLines": {"color": "#242732"}, "horzLines": {"color": "#242732"}},
                "timeScale": {"timeVisible": True, "secondsVisible": False}
            }

            series = [
                {
                    "type": "Candlestick",
                    "data": candles,
                    "options": {"upColor": "#089981", "downColor": "#f23645", "borderVisible": False}
                },
                {
                    "type": "Line",
                    "data": indicator_data,
                    "options": {"color": "#2962FF", "lineWidth": 2, "title": "EMA 20"}
                }
            ]

            # चार्ट रेंडर करना
            with col2:
                renderLightweightCharts([{"chart": chart_options, "series": series}], 'live_chart')

            # --- 5. लाइव अपडेट (Auto-Refresh) ---
            # हर 3 सेकंड में पेज रीफ्रेश होगा ताकि नई कैंडल/प्राइस अपडेट हो सके
            time.sleep(3)
            st.rerun()

        else:
            st.warning("बाज़ार बंद है या टोकन गलत है।")
            
    except Exception as e:
        st.error(f"डेटा लाने में समस्या: {e}")
else:
    st.info("👈 चार्ट देखने के लिए बाईं ओर अपने Angel One क्रेडेंशियल्स डालकर लॉगिन करें।")
