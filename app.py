import streamlit as st
import requests


st.set_page_config(
    page_title="J-Quants接続テスト",
    page_icon="🧪"
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
    type="primary"
):

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        st.write(
            "HTTPステータスコード：",
            response.status_code
        )

        st.write(
            "レスポンスの先頭部分："
        )

        st.code(
            response.text[:3000]
        )

    except Exception as e:
        st.error(
            f"接続時にエラーが発生しました：{e}"
        )
