import pandas as pd
import requests
import streamlit as st

from analysis import calculate_market_analysis

st.set_page_config(
    page_title="J-Quants接続テスト",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 J-Quants 接続テスト")

api_key = st.secrets["JQUANTS_API_KEY"]

url = (
    "https://api.jquants.com/v2/"
    "derivatives/bars/daily/options/225"
)

headers = {
    "x-api-key": api_key
}

params = {
    "date": "20260730"
}


if st.button(
    "J-Quantsへ接続する",
    type="primary",
):

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        response_data = response.json()

        records = response_data.get("data", [])

        option_df = pd.DataFrame(records)

        result = calculate_market_analysis(
            option_df=option_df,
            analysis_days=5,
        )
        
        st.success(
            f"J-Quants接続成功！"
            f"{len(option_df):,}件取得しました。"
        )
st.subheader("📊 実データ需給分析")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="現在値",
        value=f"{result['current_price']:,.0f}円",
    )

with col2:
    st.metric(
        label="Call重心",
        value=f"{result['call_center']:,.0f}円",
        delta=f"現在値から {result['call_distance']:,.0f}円",
    )

with col3:
    st.metric(
        label="Put重心",
        value=f"{result['put_center']:,.0f}円",
        delta=f"現在値から {result['put_distance']:,.0f}円",
    )
        
        st.subheader("📋 取得データの先頭5行")

        st.dataframe(
            option_df.head(),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("🔎 列名一覧")

        st.write(option_df.columns.tolist())

    except requests.exceptions.RequestException as e:
        st.error(
            f"J-Quantsへの接続に失敗しました：{e}"
        )

    except Exception as e:
        st.error(
            f"データ処理中にエラーが発生しました：{e}"
        )
