import streamlit as st


st.set_page_config(
    page_title="日経225需給分析 Ver.4",
    page_icon="📈",
    layout="wide"
)


st.title("📈 日経225需給分析 Ver.4")

st.write(
    "J-Quantsのオプションデータを使って、"
    "日経225の需給を分析するアプリです。"
)

st.success("Streamlitアプリの起動に成功しました！")

st.subheader("現在の開発状況")

st.write("✅ J-Quants API接続")
st.write("✅ Call・Put建玉分析")
st.write("✅ 建玉重心マップ")
st.write("✅ 重心距離分析")
st.write("✅ 総合需給スコア")

st.info(
    "次のステップで、Colabの分析機能を"
    "この画面へ順番に移植します。"
)
