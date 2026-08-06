from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

from analysis import calculate_market_analysis
from jquants_api import fetch_latest_option_data

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


def fetch_latest_option_data(
    url: str,
    headers: dict,
    max_lookback_days: int = 10,
):
    """
    今日から過去へさかのぼり、
    データが存在する最新日のオプションデータを取得します。
    """

    for days_ago in range(max_lookback_days + 1):
        target_date = date.today() - timedelta(days=days_ago)
        date_text = target_date.strftime("%Y%m%d")

        response = requests.get(
            url,
            headers=headers,
            params={
                "date": date_text,
            },
            timeout=30,
        )

        response.raise_for_status()

        response_data = response.json()
        records = response_data.get("data", [])

        if records:
            option_df = pd.DataFrame(records)

            return (
                option_df,
                target_date,
            )

    raise ValueError(
        f"直近{max_lookback_days}日以内に"
        "オプションデータが見つかりませんでした。"
    )

def fetch_previous_option_data(
    url: str,
    headers: dict,
    latest_date: date,
    max_lookback_days: int = 10,
):
    """
    最新営業日の前日から過去へさかのぼり、
    データが存在する直前営業日のオプションデータを取得します。
    """

    for days_ago in range(1, max_lookback_days + 1):
        target_date = latest_date - timedelta(days=days_ago)
        date_text = target_date.strftime("%Y%m%d")

        response = requests.get(
            url,
            headers=headers,
            params={
                "date": date_text,
            },
            timeout=30,
        )

        response.raise_for_status()

        response_data = response.json()
        records = response_data.get("data", [])

        if records:
            previous_df = pd.DataFrame(records)

            return (
                previous_df,
                target_date,
            )

    raise ValueError(
        f"{latest_date:%Y年%m月%d日}より前の"
        f"直近{max_lookback_days}日以内に"
        "オプションデータが見つかりませんでした。"
    )

if st.button(
    "J-Quantsへ接続する",
    type="primary",
):

    try:
        option_df, data_date = fetch_latest_option_data(
            url=url,
            headers=headers,
            max_lookback_days=10,
        )

        previous_df, previous_date = fetch_previous_option_data(
            url=url,
            headers=headers,
            latest_date=data_date,
            max_lookback_days=10,
        )

        result = calculate_market_analysis(
            option_df=option_df,
            analysis_days=5,
        )
        
        st.success(
            f"J-Quants接続成功！"
            f"{data_date:%Y年%m月%d日}のデータを"
            f"{len(option_df):,}件取得しました。"
        )
        
        st.info(
            f"比較対象："
            f"{previous_date:%Y年%m月%d日}のデータを"
            f"{len(previous_df):,}件取得しました。"
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

        lower_price = result["current_price"] * 0.8
        upper_price = result["current_price"] * 1.2

        top_oi_df = top_oi_df[
            (top_oi_df["CM"].astype(str) == nearest_cm)
            & (top_oi_df["OI"] > 0)
            & (top_oi_df["Strike"] >= lower_price)
            & (top_oi_df["Strike"] <= upper_price)
        ].copy()

        top_oi_df = (
            top_oi_df
            .groupby(
                ["PCDiv", "Strike"],
                as_index=False,
            )["OI"]
            .sum()
        )

        top_oi_df["現在値との差"] = (
            top_oi_df["Strike"]
            - result["current_price"]
        ).abs()

        top_call_df = (
            top_oi_df[top_oi_df["PCDiv"] == 2]
            .sort_values("OI", ascending=False)
            .head(5)
            [["Strike", "OI", "現在値との差"]]
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
            [["Strike", "OI", "現在値との差"]]
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
        
        st.subheader("🤖 自動需給コメント")

        if not top_call_df.empty:
            strongest_call_strike = top_call_df.iloc[0]["権利行使価格"]
            strongest_call_oi = top_call_df.iloc[0]["建玉"]
        else:
            strongest_call_strike = None
            strongest_call_oi = 0

        if not top_put_df.empty:
            strongest_put_strike = top_put_df.iloc[0]["権利行使価格"]
            strongest_put_oi = top_put_df.iloc[0]["建玉"]
        else:
            strongest_put_strike = None
            strongest_put_oi = 0

        comment_parts = []

        comment_parts.append(
            f"現在値は {result['current_price']:,.0f}円で、"
            f"建玉レンジの {result['position_ratio']:.1f}% に位置しています。"
        )

        if strongest_call_strike is not None:
            comment_parts.append(
                f"Call建玉は {strongest_call_strike:,.0f}円に"
                f"最も集中しており、建玉は {strongest_call_oi:,.0f}枚です。"
                f"この水準は上値側で意識される可能性があります。"
            )

        if strongest_put_strike is not None:
            comment_parts.append(
                f"Put建玉は {strongest_put_strike:,.0f}円に"
                f"最も集中しており、建玉は {strongest_put_oi:,.0f}枚です。"
                f"この水準は下値側で意識される可能性があります。"
            )

        if result["nearest_center"] == "Call側":
            comment_parts.append(
                "現在値はPut重心よりCall重心に近く、"
                "建玉レンジ内では上側に位置しています。"
            )
        elif result["nearest_center"] == "Put側":
            comment_parts.append(
                "現在値はCall重心よりPut重心に近く、"
                "建玉レンジ内では下側に位置しています。"
            )
        else:
            comment_parts.append(
                "現在値はCall重心とPut重心のほぼ中間に位置しています。"
            )

        market_comment = " ".join(comment_parts)

        st.info(market_comment)

        st.subheader("🛡️ サポート・レジスタンス")

        support_df = (
            top_put_df
            .sort_values("建玉", ascending=False)
            .head(3)
        )

        resistance_df = (
            top_call_df
            .sort_values("建玉", ascending=False)
            .head(3)
        )

        left_col, right_col = st.columns(2)

        with left_col:
            st.success("### 🟢 サポート候補")

            for _, row in support_df.iterrows():
                st.write(
                    f"**{row['権利行使価格']:,.0f}円** "
                    f"(建玉 {row['建玉']:,.0f}枚)"
                )

        with right_col:
            st.error("### 🔴 レジスタンス候補")

            for _, row in resistance_df.iterrows():
                st.write(
                    f"**{row['権利行使価格']:,.0f}円** "
                    f"(建玉 {row['建玉']:,.0f}枚)"
                )

        st.subheader("🎯 直近の重要価格帯")

        current_price = result["current_price"]

        support_candidates = top_put_df[
            top_put_df["権利行使価格"] < current_price
        ].copy()

        resistance_candidates = top_call_df[
            top_call_df["権利行使価格"] > current_price
        ].copy()

        if not support_candidates.empty:
            nearest_support = (
                support_candidates
                .sort_values("権利行使価格", ascending=False)
                .iloc[0]["権利行使価格"]
            )
            support_distance = current_price - nearest_support
        else:
            nearest_support = None
            support_distance = None

        if not resistance_candidates.empty:
            nearest_resistance = (
                resistance_candidates
                .sort_values("権利行使価格", ascending=True)
                .iloc[0]["権利行使価格"]
            )
            resistance_distance = nearest_resistance - current_price
        else:
            nearest_resistance = None
            resistance_distance = None

        price_col1, price_col2, price_col3 = st.columns(3)

        with price_col1:
            if nearest_support is not None:
                st.metric(
                    label="直近サポート",
                    value=f"{nearest_support:,.0f}円",
                    delta=f"現在値から下へ {support_distance:,.0f}円",
                    delta_color="off",
                )
            else:
                st.metric(
                    label="直近サポート",
                    value="該当なし",
                )

        with price_col2:
            st.metric(
                label="現在値",
                value=f"{current_price:,.0f}円",
            )

        with price_col3:
            if nearest_resistance is not None:
                st.metric(
                    label="直近レジスタンス",
                    value=f"{nearest_resistance:,.0f}円",
                    delta=f"現在値から上へ {resistance_distance:,.0f}円",
                    delta_color="off",
                )
            else:
                st.metric(
                    label="直近レジスタンス",
                    value="該当なし",
                )

        if (
            nearest_support is not None
            and nearest_resistance is not None
        ):
            expected_range = nearest_resistance - nearest_support

            st.info(
                f"現在の注目レンジは "
                f"{nearest_support:,.0f}円〜"
                f"{nearest_resistance:,.0f}円です。"
                f"レンジ幅は約 {expected_range:,.0f}円です。"
            )

            range_position = (
                (current_price - nearest_support)
                / expected_range
                * 100
            )

            range_position = max(
                0.0,
                min(100.0, range_position),
            )

            if range_position >= 70:
                range_judgment = "レジスタンス寄り"
                range_message = (
                    "現在値は注目レンジの上側にあります。"
                    "直近レジスタンスへの接近に注意が必要です。"
                )
            elif range_position <= 30:
                range_judgment = "サポート寄り"
                range_message = (
                    "現在値は注目レンジの下側にあります。"
                    "直近サポートの反応が注目されます。"
                )
            else:
                range_judgment = "レンジ中央"
                range_message = (
                    "現在値は注目レンジの中央付近にあります。"
                    "上下どちらかへの離脱待ちの状態です。"
                )

            position_col1, position_col2 = st.columns(2)

            with position_col1:
                st.metric(
                    label="レンジ内位置",
                    value=f"{range_position:.1f}%",
                )

            with position_col2:
                st.metric(
                    label="現在位置の判定",
                    value=range_judgment,
                )

            st.progress(
                int(range_position)
            )

            st.info(range_message)

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
