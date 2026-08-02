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

        st.subheader("⭐ 総合需給判定")
    
        judge_col1, judge_col2 = st.columns(2)
        
        with judge_col1:
            st.metric(
                label="総合需給スコア",
                value=f"{result['total_score']:.1f}点",
            )
        
        with judge_col2:
            st.metric(
                label="需給判定",
                value=result["market_judgment"],
            )
        
        st.write(
            f"評価：{result['stars']}"
        )
        
        st.info(
            f"現在値は建玉レンジの "
            f"{result['position_ratio']:.1f}% の位置です。"
            f"最も近い重心は「{result['nearest_center']}」です。"
        )
        
        st.subheader("🎯 現在値に近い建玉ランキング")

        ranking_df = option_df.copy()

        for column in ["Strike", "OI", "PCDiv"]:
            ranking_df[column] = pd.to_numeric(
                ranking_df[column],
                errors="coerce",
            )

        ranking_df = ranking_df.dropna(
            subset=["CM", "Strike", "OI", "PCDiv"]
        )

        nearest_cm = sorted(
            ranking_df["CM"].astype(str).unique()
        )[0]

        ranking_df = ranking_df[
            (ranking_df["CM"].astype(str) == nearest_cm)
            & (ranking_df["OI"] > 0)
        ].copy()

        ranking_df = (
            ranking_df
            .groupby(
                ["PCDiv", "Strike"],
                as_index=False,
            )["OI"]
            .sum()
        )

        ranking_df["区分"] = (
            ranking_df["PCDiv"]
            .map({
                1: "Put",
                2: "Call",
            })
            .fillna("不明")
        )

        ranking_df["現在値との差"] = (
            ranking_df["Strike"]
            - result["current_price"]
        ).abs()

        ranking_df = (
            ranking_df
            .sort_values(
                ["現在値との差", "OI"],
                ascending=[True, False],
            )
            .head(10)
        )

        ranking_df = ranking_df[
            ["区分", "Strike", "OI", "現在値との差"]
        ].rename(
            columns={
                "Strike": "権利行使価格",
                "OI": "建玉",
            }
        )

        st.dataframe(
            ranking_df,
            width="stretch",
            hide_index=True,
        )

        st.subheader("🔥 建玉集中ゾーン")

        top_oi_df = option_df.copy()

        for column in ["Strike", "OI", "PCDiv"]:
            top_oi_df[column] = pd.to_numeric(
                top_oi_df[column],
                errors="coerce",
            )

        top_oi_df = top_oi_df.dropna(
            subset=["CM", "Strike", "OI", "PCDiv"]
        )

        top_oi_df = top_oi_df[
            (top_oi_df["CM"].astype(str) == nearest_cm)
            & (top_oi_df["OI"] > 0)
        ].copy()

        top_oi_df = (
            top_oi_df
            .groupby(
                ["PCDiv", "Strike"],
                as_index=False,
            )["OI"]
            .sum()
        )

        top_call_df = (
            top_oi_df[top_oi_df["PCDiv"] == 2]
            .sort_values("OI", ascending=False)
            .head(5)
            [["Strike", "OI"]]
            .rename(
                columns={
                    "Strike": "権利行使価格",
                    "OI": "建玉",
                }
            )
        )

        top_put_df = (
            top_oi_df[top_oi_df["PCDiv"] == 1]
            .sort_values("OI", ascending=False)
            .head(5)
            [["Strike", "OI"]]
            .rename(
                columns={
                    "Strike": "権利行使価格",
                    "OI": "建玉",
                }
            )
        )

        call_zone_col, put_zone_col = st.columns(2)

        with call_zone_col:
            st.markdown("#### 📈 Call建玉 上位5")
            st.dataframe(
                top_call_df,
                width="stretch",
                hide_index=True,
            )

        with put_zone_col:
            st.markdown("#### 📉 Put建玉 上位5")
            st.dataframe(
                top_put_df,
                width="stretch",
                hide_index=True,
            )
        
        st.subheader("📋 取得データの先頭5行")

        st.dataframe(
            option_df.head(),
            width="stretch",
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
