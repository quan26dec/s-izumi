import streamlit as st

st.set_page_config(page_title="J-Quants接続テスト")

st.title("🧪 J-Quants 接続テスト")

try:
    api_key = st.secrets["JQUANTS_API_KEY"]

    st.success("✅ APIキーを読み込めました！")

    st.write("APIキーの先頭5文字")

    st.code(api_key[:5] + "*****")

except Exception as e:

    st.error("APIキーを読み込めませんでした。")

    st.exception(e)
