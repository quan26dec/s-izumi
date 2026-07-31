import pandas as pd
import requests
import streamlit as st


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

        st.success(
            f"J-Quants接続成功！"
            f"{len(option_df):,}件取得しました。"
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
