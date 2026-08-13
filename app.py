from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

from analysis import calculate_market_analysis

st.set_page_config(
    page_title="J-Quants接続テスト",
    page_icon="🧪",
    layout="wide",
)

st.title("📊 日経225 オプション需給分析")

summary_placeholder = st.empty()

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

        two_days_ago_df, two_days_ago_date = fetch_previous_option_data(
            url=url,
            headers=headers,
            latest_date=previous_date,
            max_lookback_days=10,
        )

        previous_oi_df_for_compare = previous_df.copy()
        two_days_ago_oi_df = two_days_ago_df.copy()

        for column in ["Strike", "OI", "PCDiv"]:
            previous_oi_df_for_compare[column] = pd.to_numeric(
                previous_oi_df_for_compare[column],
                errors="coerce",
            )

            two_days_ago_oi_df[column] = pd.to_numeric(
                two_days_ago_oi_df[column],
                errors="coerce",
            )

        previous_oi_df_for_compare = (
            previous_oi_df_for_compare
            .groupby(
                ["PCDiv", "Strike"],
                as_index=False,
            )["OI"]
            .sum()
        )

        two_days_ago_oi_df = (
            two_days_ago_oi_df
            .groupby(
                ["PCDiv", "Strike"],
                as_index=False,
            )["OI"]
            .sum()
        )

        previous_change_df = pd.merge(
            previous_oi_df_for_compare,
            two_days_ago_oi_df,
            on=["PCDiv", "Strike"],
            how="outer",
            suffixes=("_previous", "_two_days_ago"),
        )

        previous_change_df[
            ["OI_previous", "OI_two_days_ago"]
        ] = previous_change_df[
            ["OI_previous", "OI_two_days_ago"]
        ].fillna(0)

        previous_change_df["OI_change"] = (
            previous_change_df["OI_previous"]
            - previous_change_df["OI_two_days_ago"]
        )

        previous_change_df["区分"] = (
            previous_change_df["PCDiv"]
            .map({
                1: "Put",
                2: "Call",
            })
            .fillna("不明")
        )

        result = calculate_market_analysis(
            option_df=option_df,
            analysis_days=5,
        )

        previous_result = calculate_market_analysis(
            option_df=previous_df,
            analysis_days=5,
        )

        previous_current_price = previous_result["current_price"]

        previous_near_lower = previous_current_price * 0.90
        previous_near_upper = previous_current_price * 1.10

        previous_near_change_df = previous_change_df[
            (previous_change_df["Strike"] >= previous_near_lower)
            & (previous_change_df["Strike"] <= previous_near_upper)
            & (previous_change_df["OI_change"] > 0)
        ].copy()

        previous_distance_weight_df = previous_near_change_df.copy()

        previous_distance_weight_df["現在値との差"] = (
            previous_distance_weight_df["Strike"]
            - previous_current_price
        ).abs()

        previous_distance_weight_df["距離ウェイト"] = (
            1
            / (
                1
                + previous_distance_weight_df["現在値との差"]
                / previous_current_price
                * 100
            )
        )

        previous_distance_weight_df["加重建玉増加"] = (
            previous_distance_weight_df["OI_change"]
            * previous_distance_weight_df["距離ウェイト"]
        )

        previous_call_weighted_score = (
            previous_distance_weight_df[
                previous_distance_weight_df["区分"] == "Call"
            ]["加重建玉増加"]
            .sum()
        )

        previous_put_weighted_score = (
            previous_distance_weight_df[
                previous_distance_weight_df["区分"] == "Put"
            ]["加重建玉増加"]
            .sum()
        )

        previous_weighted_total = (
            previous_call_weighted_score
            + previous_put_weighted_score
        )

        if previous_weighted_total > 0:
            previous_call_weighted_share = (
                previous_call_weighted_score
                / previous_weighted_total
                * 100
            )
            previous_put_weighted_share = (
                100 - previous_call_weighted_share
            )
        else:
            previous_call_weighted_share = 50.0
            previous_put_weighted_share = 50.0


        st.caption(
            f"✅ 最新：{data_date:%Y年%m月%d日} "
            f"（{len(option_df):,}件）"
            f"　｜　比較：{previous_date:%Y年%m月%d日} "
            f"（{len(previous_df):,}件）"
        )
        
        st.subheader("📈 建玉増減ランキング")

        latest_oi_df = option_df.copy()
        previous_oi_df = previous_df.copy()

        for column in ["Strike", "OI", "PCDiv"]:
            latest_oi_df[column] = pd.to_numeric(
                latest_oi_df[column],
                errors="coerce",
            )

            previous_oi_df[column] = pd.to_numeric(
                previous_oi_df[column],
                errors="coerce",
            )

        latest_oi_df = latest_oi_df.dropna(
            subset=["CM", "Strike", "OI", "PCDiv"]
        )

        previous_oi_df = previous_oi_df.dropna(
            subset=["CM", "Strike", "OI", "PCDiv"]
        )

        latest_oi_df = (
            latest_oi_df
            .groupby(
                ["PCDiv", "Strike"],
                as_index=False,
            )["OI"]
            .sum()
        )

        previous_oi_df = (
            previous_oi_df
            .groupby(
                ["PCDiv", "Strike"],
                as_index=False,
            )["OI"]
            .sum()
        )

        oi_change_df = pd.merge(
            latest_oi_df,
            previous_oi_df,
            on=["PCDiv", "Strike"],
            how="outer",
            suffixes=("_latest", "_previous"),
        )

        oi_change_df[
            ["OI_latest", "OI_previous"]
        ] = oi_change_df[
            ["OI_latest", "OI_previous"]
        ].fillna(0)

        oi_change_df["OI_change"] = (
            oi_change_df["OI_latest"]
            - oi_change_df["OI_previous"]
        )

        oi_change_df["区分"] = (
            oi_change_df["PCDiv"]
            .map({
                1: "Put",
                2: "Call",
            })
            .fillna("不明")
        )

        call_ranking = (
        oi_change_df[
            (oi_change_df["区分"] == "Call")
            & (oi_change_df["OI_change"] > 0)
        ]
        .sort_values("OI_change", ascending=False)
        .head(10)
    )

        put_ranking = (
            oi_change_df[
                (oi_change_df["区分"] == "Put")
                & (oi_change_df["OI_change"] > 0)
            ]
            .sort_values("OI_change", ascending=False)
            .head(10)
        )

        call_decrease_ranking = (
            oi_change_df[
                (oi_change_df["区分"] == "Call")
                & (oi_change_df["OI_change"] < 0)
            ]
            .sort_values("OI_change", ascending=True)
            .head(10)
        )

        put_decrease_ranking = (
            oi_change_df[
                (oi_change_df["区分"] == "Put")
                & (oi_change_df["OI_change"] < 0)
            ]
            .sort_values("OI_change", ascending=True)
            .head(10)
        )

        if not call_ranking.empty and not put_ranking.empty:
            top_call = call_ranking.iloc[0]
            top_put = put_ranking.iloc[0]

            st.info(
                f"📌 本日の建玉変化："
                f"Put {top_put['Strike']:,.0f}円に +{top_put['OI_change']:,.0f}枚 "
                f"｜ Call {top_call['Strike']:,.0f}円に +{top_call['OI_change']:,.0f}枚"
            )

        with st.expander("▲ 建玉増加ランキング", expanded=False):

            ranking_col1, ranking_col2 = st.columns(2)

            with ranking_col1:
                st.markdown("#### 📈 Call建玉増加 TOP10")
                st.dataframe(
                    call_ranking[
                        [
                            "Strike",
                            "OI_previous",
                            "OI_latest",
                            "OI_change",
                        ]
                    ].rename(
                        columns={
                            "Strike": "権利行使価格",
                            "OI_previous": "前日建玉",
                            "OI_latest": "当日建玉",
                            "OI_change": "建玉増減",
                        }
                    ),
                    width="stretch",
                    hide_index=True,
                )

            with ranking_col2:
                st.markdown("#### 📉 Put建玉増加 TOP10")
                st.dataframe(
                    put_ranking[
                        [
                            "Strike",
                            "OI_previous",
                            "OI_latest",
                            "OI_change",
                        ]
                    ].rename(
                        columns={
                            "Strike": "権利行使価格",
                            "OI_previous": "前日建玉",
                            "OI_latest": "当日建玉",
                            "OI_change": "建玉増減",
                        }
                    ),
                    width="stretch",
                    hide_index=True,
                )    


        with st.expander("▼ 建玉減少ランキング", expanded=False):   

            ranking_col3, ranking_col4 = st.columns(2)

            with ranking_col3:
                st.markdown("#### 🔻 Call建玉減少 TOP10")
                st.dataframe(
                    call_decrease_ranking[
                        [
                            "Strike",
                            "OI_previous",
                            "OI_latest",
                            "OI_change",
                        ]
                    ].rename(
                        columns={
                            "Strike": "権利行使価格",
                            "OI_previous": "前日建玉",
                            "OI_latest": "当日建玉",
                            "OI_change": "建玉増減",
                        }
                    ),
                    width="stretch",
                    hide_index=True,
                )

        with ranking_col4:
            st.markdown("#### 🔻 Put建玉減少 TOP10")
            st.dataframe(
                put_decrease_ranking[
                    [
                        "Strike",
                        "OI_previous",
                        "OI_latest",
                        "OI_change",
                    ]
                ].rename(
                    columns={
                        "Strike": "権利行使価格",
                        "OI_previous": "前日建玉",
                        "OI_latest": "当日建玉",
                        "OI_change": "建玉増減",
                    }
                ),
                width="stretch",
                hide_index=True,
            )

        st.markdown("### 📌 建玉増減サマリー")

        summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

        if not call_ranking.empty:
            with summary_col1:
                top_call_up = call_ranking.iloc[0]
                st.metric(
                    "Call 最大増加",
                    f"{top_call_up['Strike']:,.0f}円",
                    f"+{top_call_up['OI_change']:,.0f}枚 ｜ 現在値から {top_call_up['Strike'] - result['current_price']:+,.0f}円",
                )

        if not put_ranking.empty:
            with summary_col2:
                top_put_up = put_ranking.iloc[0]
                st.metric(
                    "Put 最大増加",
                    f"{top_put_up['Strike']:,.0f}円",
                    f"+{top_put_up['OI_change']:,.0f}枚 ｜ 現在値から {top_put_up['Strike'] - result['current_price']:+,.0f}円",
                )

        if not call_decrease_ranking.empty:
            with summary_col3:
                top_call_down = call_decrease_ranking.iloc[0]
                st.metric(
                    "Call 最大減少",
                    f"{top_call_down['Strike']:,.0f}円",
                    f"{top_call_down['OI_change']:,.0f}枚 ｜ 現在値から {top_call_down['Strike'] - result['current_price']:+,.0f}円",
                )

        if not put_decrease_ranking.empty:
            with summary_col4:
                top_put_down = put_decrease_ranking.iloc[0]
                st.metric(
                    "Put 最大減少",
                    f"{top_put_down['Strike']:,.0f}円",
                    f"{top_put_down['OI_change']:,.0f}枚 ｜ 現在値から {top_put_down['Strike'] - result['current_price']:+,.0f}円",
                )

        st.markdown("### 🎯 現在値周辺の建玉増加")

        near_lower = result["current_price"] * 0.90
        near_upper = result["current_price"] * 1.10

        near_oi_change_df = oi_change_df[
            (oi_change_df["Strike"] >= near_lower)
            & (oi_change_df["Strike"] <= near_upper)
            & (oi_change_df["OI_change"] > 0)
        ].copy()

        near_oi_change_df["現在値との差"] = (
            near_oi_change_df["Strike"]
            - result["current_price"]
        ).abs()

        near_call_increase = (
            near_oi_change_df[
                near_oi_change_df["区分"] == "Call"
            ]
            .sort_values("OI_change", ascending=False)
            .head(5)
        )

        near_put_increase = (
            near_oi_change_df[
                near_oi_change_df["区分"] == "Put"
            ]
            .sort_values("OI_change", ascending=False)
            .head(5)
        )

        if not near_call_increase.empty and not near_put_increase.empty:
            nearest_call = near_call_increase.sort_values("現在値との差").iloc[0]
            nearest_put = near_put_increase.sort_values("現在値との差").iloc[0]

            call_distance = nearest_call["Strike"] - result["current_price"]
            put_distance = nearest_put["Strike"] - result["current_price"]

            st.info(
                f"🎯 直近建玉増加："
                f"Call {nearest_call['Strike']:,.0f}円 "
                f"+{nearest_call['OI_change']:,.0f}枚 "
                f"（現在値から {call_distance:+,.0f}円）"
                f" ｜ "
                f"Put {nearest_put['Strike']:,.0f}円 "
                f"+{nearest_put['OI_change']:,.0f}枚 "
                f"（現在値から {put_distance:+,.0f}円）"
            )

        near_col1, near_col2 = st.columns(2)

        with near_col1:
            st.markdown("#### 📈 Call 現在値周辺 TOP5")
            st.dataframe(
                near_call_increase[
                    [
                        "Strike",
                        "OI_previous",
                        "OI_latest",
                        "OI_change",
                        "現在値との差",
                    ]
                ].rename(
                    columns={
                        "Strike": "権利行使価格",
                        "OI_previous": "前日建玉",
                        "OI_latest": "当日建玉",
                        "OI_change": "建玉増減",
                    }
                ),
                width="stretch",
                hide_index=True,
            )

        with near_col2:
            st.markdown("#### 📉 Put 現在値周辺 TOP5")
            st.dataframe(
                near_put_increase[
                    [
                        "Strike",
                        "OI_previous",
                        "OI_latest",
                        "OI_change",
                        "現在値との差",
                    ]
                ].rename(
                    columns={
                        "Strike": "権利行使価格",
                        "OI_previous": "前日建玉",
                        "OI_latest": "当日建玉",
                        "OI_change": "建玉増減",
                    }
                ),
                width="stretch",
                hide_index=True,
            )

        st.markdown("### ⚖️ 現在値周辺の建玉変化バランス（単純集計）")  

        near_call_increase_sum = near_call_increase["OI_change"].sum()
        near_put_increase_sum = near_put_increase["OI_change"].sum()

        near_total_increase = (
            near_call_increase_sum
            + near_put_increase_sum
        )

        if near_total_increase > 0:
            near_call_share = (
                near_call_increase_sum
                / near_total_increase
                * 100
            )
            near_put_share = 100 - near_call_share
        else:
            near_call_share = 50.0
            near_put_share = 50.0

        if near_call_share >= 60:
            near_balance_judgment = "Call側の建玉増加が優勢"
        elif near_put_share >= 60:
            near_balance_judgment = "Put側の建玉増加が優勢"
        else:
            near_balance_judgment = "Call・Putが拮抗"

        balance_col1, balance_col2, balance_col3 = st.columns(3)

        with balance_col1:
            st.metric(
                "Call建玉増加 合計",
                f"{near_call_increase_sum:,.0f}枚",
                f"{near_call_share:.1f}%",
            )

        with balance_col2:
            st.metric(
                "Put建玉増加 合計",
                f"{near_put_increase_sum:,.0f}枚",
                f"{near_put_share:.1f}%",
            )

        with balance_col3:
            st.metric(
                "建玉変化バランス",
                near_balance_judgment,
            )

        st.progress(int(near_call_share))

        st.caption(
            "左ほどPut側、右ほどCall側の建玉増加が優勢です。"
        )

        st.markdown("### 🎯 距離加重・建玉変化スコア")

        distance_weight_df = near_oi_change_df.copy()

        distance_weight_df["現在値との差"] = (
            distance_weight_df["Strike"]
            - result["current_price"]
        ).abs()

        distance_weight_df["距離ウェイト"] = (
            1
            / (
                1
                + distance_weight_df["現在値との差"]
                / result["current_price"]
                * 100
            )
        )

        distance_weight_df["加重建玉増加"] = (
            distance_weight_df["OI_change"]
            * distance_weight_df["距離ウェイト"]
        )

        call_weighted_score = (
            distance_weight_df[
                distance_weight_df["区分"] == "Call"
            ]["加重建玉増加"]
            .sum()
        )

        put_weighted_score = (
            distance_weight_df[
                distance_weight_df["区分"] == "Put"
            ]["加重建玉増加"]
            .sum()
        )

        weighted_total = (
            call_weighted_score
            + put_weighted_score
        )

        if weighted_total > 0:
            call_weighted_share = (
                call_weighted_score
                / weighted_total
                * 100
            )
            put_weighted_share = 100 - call_weighted_share
        else:
            call_weighted_share = 50.0
            put_weighted_share = 50.0

        if call_weighted_share >= 60:
            weighted_judgment = "Call側優勢"
        elif put_weighted_share >= 60:
            weighted_judgment = "Put側優勢"
        else:
            weighted_judgment = "拮抗"

        call_share_change = (
            call_weighted_share
            - previous_call_weighted_share
        )

        put_share_change = (
            put_weighted_share
            - previous_put_weighted_share
        )

        if call_share_change >= 5:
            flow_change_judgment = "Call側へ強くシフト"
        elif call_share_change >= 2:
            flow_change_judgment = "Call側へややシフト"
        elif call_share_change <= -5:
            flow_change_judgment = "Put側へ強くシフト"
        elif call_share_change <= -2:
            flow_change_judgment = "Put側へややシフト"
        else:
            flow_change_judgment = "ほぼ横ばい"

        st.info(
            f"🎯 距離加重判定：{weighted_judgment} ｜ "
            f"Call {call_weighted_share:.1f}% / "
            f"Put {put_weighted_share:.1f}% ｜ "
            f"前日比：{flow_change_judgment} "
            f"(Call {call_share_change:+.1f}pt)"
        )

        weighted_col1, weighted_col2, weighted_col3 = st.columns(3)

        with weighted_col1:
            st.metric(
                "Call距離加重比率",
                f"{call_weighted_share:.1f}%",
            )

        with weighted_col2:
            st.metric(
                "Put距離加重比率",
                f"{put_weighted_share:.1f}%",
            )

        with weighted_col3:
            st.metric(
                "距離加重判定",
                weighted_judgment,
            )

        st.info(
            f"🔎 集計比較："
            f"単純集計では「{near_balance_judgment}」 ｜ "
            f"距離加重では「{weighted_judgment}」"
        )

        if (
            "Call" in near_balance_judgment
            and "Call" in weighted_judgment
        ):
            comparison_judgment = "🟢 Call優勢で一致"

        elif (
            "Put" in near_balance_judgment
            and "Put" in weighted_judgment
        ):
            comparison_judgment = "🔴 Put優勢で一致"

        elif (
            "拮抗" in near_balance_judgment
            or "拮抗" in weighted_judgment
        ):
            comparison_judgment = "🟡 方向感はまだ不明瞭"

        else:
            comparison_judgment = "⚠️ 単純集計と距離加重が逆行"

        st.caption(f"需給シグナル整合性：{comparison_judgment}")

        st.markdown("#### 🔄 前日からの需給変化")

        flow_col1, flow_col2, flow_col3 = st.columns(3)

        with flow_col1:
            st.metric(
                "前日 Call比率",
                f"{previous_call_weighted_share:.1f}%",
            )

        with flow_col2:
            st.metric(
                "現在 Call比率",
                f"{call_weighted_share:.1f}%",
                delta=f"{call_share_change:+.1f}pt",
            )

        with flow_col3:
            st.metric(
                "需給変化判定",
                flow_change_judgment,
            )

        st.info(
            f"現在の建玉バランスは「{weighted_judgment}」。"
            f"前日比では「{flow_change_judgment}」です。"
        )

        if weighted_judgment == "Call側優勢":
            if call_share_change >= 5:
                total_flow_signal = "🚀 Call優勢が強まり中"
            elif call_share_change <= -5:
                total_flow_signal = "⚠️ Call優勢だがPut方向へ急変"
            else:
                total_flow_signal = "📈 Call優勢を維持"

        elif weighted_judgment == "Put側優勢":
            if call_share_change <= -5:
                total_flow_signal = "🚨 Put優勢が強まり中"
            elif call_share_change >= 5:
                total_flow_signal = "⚠️ Put優勢だがCall方向へ急変"
            else:
                total_flow_signal = "📉 Put優勢を維持"

        else:
            if call_share_change >= 5:
                total_flow_signal = "↗️ 拮抗からCall方向へ変化"
            elif call_share_change <= -5:
                total_flow_signal = "↘️ 拮抗からPut方向へ変化"
            else:
                total_flow_signal = "⚖️ 方向感なし"

        if result["market_judgment"] in ["強気", "やや強気"]:
            if "Put" in total_flow_signal:
                state_change_interpretation = "⚠️ 強気構造に悪化シグナル"
            elif "Call" in total_flow_signal:
                state_change_interpretation = "🟢 強気構造を維持・強化"
            else:
                state_change_interpretation = "🟡 強気構造だが変化は限定的"

        elif result["market_judgment"] in ["弱気", "やや弱気"]:
            if "Call" in total_flow_signal:
                state_change_interpretation = "🔄 弱気構造に改善シグナル"
            elif "Put" in total_flow_signal:
                state_change_interpretation = "🔴 弱気構造を維持・悪化"
            else:
                state_change_interpretation = "🟡 弱気構造だが変化は限定的"

        else:
            if "Call" in total_flow_signal:
                state_change_interpretation = "↗️ 中立構造からCall方向へ変化"
            elif "Put" in total_flow_signal:
                state_change_interpretation = "↘️ 中立構造からPut方向へ変化"
            else:
                state_change_interpretation = "⚖️ 状態・変化ともに中立"

        st.info(f"🧭 状態×変化判定：{state_change_interpretation}")

        flow_score_adjustment = max(
            -10.0,
            min(
                10.0,
                call_share_change * 0.5,
            ),
        )

        adjusted_total_score = max(
            0.0,
            min(
                100.0,
                result["total_score"] + flow_score_adjustment,
            ),
        )

        if adjusted_total_score >= 70:
            adjusted_market_judgment = "強気"
        elif adjusted_total_score >= 60:
            adjusted_market_judgment = "やや強気"
        elif adjusted_total_score >= 40:
            adjusted_market_judgment = "中立"
        elif adjusted_total_score >= 30:
            adjusted_market_judgment = "やや弱気"
        else:
            adjusted_market_judgment = "弱気"

        # 状態判定と短期判定の乖離を判定
        judgment_levels = {
            "弱気": 0,
            "やや弱気": 1,
            "中立": 2,
            "やや強気": 3,
            "強気": 4,
        }

        state_level = judgment_levels[result["market_judgment"]]
        short_level = judgment_levels[adjusted_market_judgment]

        judgment_gap = short_level - state_level

        if judgment_gap >= 1:
            judgment_gap_signal = "🔄 判定改善"
        elif judgment_gap <= -1:
            judgment_gap_signal = "⚠️ 判定悪化"
        else:
            judgment_gap_signal = "➡️ 判定維持"

        st.caption(
            f"判定差：{judgment_gap_signal} "
            f"（状態：{result['market_judgment']} → 短期：{adjusted_market_judgment}）"
        )

        st.info(
            f"📊 スコア変化："
            f"状態 {result['total_score']:.1f}点 "
            f"→ 変化補正 {flow_score_adjustment:+.1f}点 "
            f"→ 短期総合 {adjusted_total_score:.1f}点 "
            f"（{adjusted_market_judgment}）"
        )

        conservative_score = max(
            0.0,
            min(100.0, result["total_score"] + call_share_change * 0.25),
        )

        standard_score = max(
            0.0,
            min(100.0, result["total_score"] + call_share_change * 0.50),
        )

        aggressive_score = max(
            0.0,
            min(100.0, result["total_score"] + call_share_change * 0.75),
        )

        st.caption(
            f"補正感度："
            f"0.25倍 → {conservative_score:.1f}点 ｜ "
            f"0.50倍 → {standard_score:.1f}点 ｜ "
            f"0.75倍 → {aggressive_score:.1f}点"
        )

        st.warning(
            f"総合変化シグナル：{total_flow_signal}"
        )

        st.progress(int(call_weighted_share))

        st.caption(
            "現在値に近い権利行使価格ほど重く評価した建玉増加バランスです。"
        )

        st.markdown("### 🧭 現在値を境にした建玉増加4象限")

        current_price = result["current_price"]

        upper_call_df = near_oi_change_df[
            (near_oi_change_df["区分"] == "Call")
            & (near_oi_change_df["Strike"] > current_price)
        ].copy()

        lower_call_df = near_oi_change_df[
            (near_oi_change_df["区分"] == "Call")
            & (near_oi_change_df["Strike"] < current_price)
        ].copy()

        upper_put_df = near_oi_change_df[
            (near_oi_change_df["区分"] == "Put")
            & (near_oi_change_df["Strike"] > current_price)
        ].copy()

        lower_put_df = near_oi_change_df[
            (near_oi_change_df["区分"] == "Put")
            & (near_oi_change_df["Strike"] < current_price)
        ].copy()

        upper_call_sum = upper_call_df["OI_change"].sum()
        lower_call_sum = lower_call_df["OI_change"].sum()
        upper_put_sum = upper_put_df["OI_change"].sum()
        lower_put_sum = lower_put_df["OI_change"].sum()

        quad_col1, quad_col2, quad_col3, quad_col4 = st.columns(4)

        with quad_col1:
            st.metric(
                "上側 Call増加",
                f"{upper_call_sum:,.0f}枚",
            )

        with quad_col2:
            st.metric(
                "下側 Put増加",
                f"{lower_put_sum:,.0f}枚",
            )

        with quad_col3:
            st.metric(
                "下側 Call増加",
                f"{lower_call_sum:,.0f}枚",
            )

        with quad_col4:
            st.metric(
                "上側 Put増加",
                f"{upper_put_sum:,.0f}枚",
            )

        main_upper_pressure = upper_call_sum + upper_put_sum
        main_lower_pressure = lower_call_sum + lower_put_sum

        main_pair = (
            upper_call_sum
            + lower_put_sum
        )

        reverse_pair = (
            lower_call_sum
            + upper_put_sum
        )

        quadrant_total = (
            main_pair
            + reverse_pair
        )

        if quadrant_total > 0:
            main_pair_share = (
                main_pair
                / quadrant_total
                * 100
            )
        else:
            main_pair_share = 0.0

        if main_pair_share >= 80:
            if upper_call_sum > lower_put_sum * 1.5:
                quadrant_judgment = "上側Call集中型"
            elif lower_put_sum > upper_call_sum * 1.5:
                quadrant_judgment = "下側Put集中型"
            else:
                quadrant_judgment = "レンジ形成型"

        elif reverse_pair > main_pair:
            quadrant_judgment = "逆配置型"

        else:
            quadrant_judgment = "方向感なし"

        st.info(
            f"4象限判定：{quadrant_judgment} "
            f"（主要2象限比率 {main_pair_share:.1f}%）"
        )

        st.markdown("### 🎯 主要攻防価格")

        if not upper_call_df.empty:
            top_upper_call = (
                upper_call_df
                .sort_values("OI_change", ascending=False)
                .iloc[0]
            )
            upper_call_strike = top_upper_call["Strike"]
            upper_call_change = top_upper_call["OI_change"]
        else:
            upper_call_strike = None
            upper_call_change = 0

        if not lower_put_df.empty:
            top_lower_put = (
                lower_put_df
                .sort_values("OI_change", ascending=False)
                .iloc[0]
            )
            lower_put_strike = top_lower_put["Strike"]
            lower_put_change = top_lower_put["OI_change"]
        else:
            lower_put_strike = None
            lower_put_change = 0

        battle_col1, battle_col2, battle_col3 = st.columns(3)

        with battle_col1:
            if lower_put_strike is not None:
                st.metric(
                    "下側Put主要価格",
                    f"{lower_put_strike:,.0f}円",
                    f"+{lower_put_change:,.0f}枚",
                )
            else:
                st.metric(
                    "下側Put主要価格",
                    "データなし",
                )

        with battle_col2:
            st.metric(
                "現在値",
                f"{current_price:,.0f}円",
            )

        with battle_col3:
            if upper_call_strike is not None:
                st.metric(
                    "上側Call主要価格",
                    f"{upper_call_strike:,.0f}円",
                    f"+{upper_call_change:,.0f}枚",
                )
            else:
                st.metric(
                    "上側Call主要価格",
                    "データなし",
                )

        if (
            lower_put_strike is not None
            and upper_call_strike is not None
        ):
            battle_range_width = (
                upper_call_strike
                - lower_put_strike
            )

            st.info(
                f"攻防レンジ候補："
                f"{lower_put_strike:,.0f}円 ～ "
                f"{upper_call_strike:,.0f}円 "
                f"（幅 {battle_range_width:,.0f}円）"
            )

        st.markdown("### 📍 直近攻防価格")

        near_lower_put = lower_put_df.copy()
        near_upper_call = upper_call_df.copy()

        near_lower_put["現在値との差"] = (
            current_price
            - near_lower_put["Strike"]
        )

        near_upper_call["現在値との差"] = (
            near_upper_call["Strike"]
            - current_price
        )

        near_lower_put = near_lower_put[
            near_lower_put["現在値との差"] >= 0
        ]

        near_upper_call = near_upper_call[
            near_upper_call["現在値との差"] >= 0
        ]

        if not near_lower_put.empty:
            nearest_put_row = (
                near_lower_put
                .sort_values(
                    ["現在値との差", "OI_change"],
                    ascending=[True, False],
                )
                .iloc[0]
            )
            nearest_put_strike = nearest_put_row["Strike"]
            nearest_put_change = nearest_put_row["OI_change"]
            nearest_put_distance = nearest_put_row["現在値との差"]
        else:
            nearest_put_strike = None
            nearest_put_change = 0
            nearest_put_distance = None

        if not near_upper_call.empty:
            nearest_call_row = (
                near_upper_call
                .sort_values(
                    ["現在値との差", "OI_change"],
                    ascending=[True, False],
                )
                .iloc[0]
            )
            nearest_call_strike = nearest_call_row["Strike"]
            nearest_call_change = nearest_call_row["OI_change"]
            nearest_call_distance = nearest_call_row["現在値との差"]
        else:
            nearest_call_strike = None
            nearest_call_change = 0
            nearest_call_distance = None

        near_battle_col1, near_battle_col2, near_battle_col3 = st.columns(3)

        with near_battle_col1:
            if nearest_put_strike is not None:
                st.metric(
                    "直近Put攻防",
                    f"{nearest_put_strike:,.0f}円",
                    f"現在値から下へ {nearest_put_distance:,.0f}円",
                )
            else:
                st.metric(
                    "直近Put攻防",
                    "データなし",
                )

        with near_battle_col2:
            st.metric(
                "現在値",
                f"{current_price:,.0f}円",
            )

        with near_battle_col3:
            if nearest_call_strike is not None:
                st.metric(
                    "直近Call攻防",
                    f"{nearest_call_strike:,.0f}円",
                    f"現在値から上へ {nearest_call_distance:,.0f}円",
                )
            else:
                st.metric(
                    "直近Call攻防",
                    "データなし",
                )

        if (
            nearest_put_strike is not None
            and nearest_call_strike is not None
        ):
            near_battle_width = (
                nearest_call_strike
                - nearest_put_strike
            )

            st.info(
                f"直近攻防レンジ："
                f"{nearest_put_strike:,.0f}円 ～ "
                f"{nearest_call_strike:,.0f}円 "
                f"（幅 {near_battle_width:,.0f}円）"
            )

        st.markdown("### 💥 攻防強度スコア")

        battle_strength_df = near_oi_change_df.copy()

        battle_strength_df["現在値との差"] = (
            battle_strength_df["Strike"]
            - current_price
        ).abs()

        battle_strength_df["距離係数"] = (
            1
            / (
                1
                + battle_strength_df["現在値との差"]
                / 250
            )
        )

        battle_strength_df["攻防強度"] = (
            battle_strength_df["OI_change"]
            * battle_strength_df["距離係数"]
        )

        upper_call_strength_df = (
            battle_strength_df[
                (battle_strength_df["区分"] == "Call")
                & (battle_strength_df["Strike"] > current_price)
            ]
            .sort_values("攻防強度", ascending=False)
        )

        lower_put_strength_df = (
            battle_strength_df[
                (battle_strength_df["区分"] == "Put")
                & (battle_strength_df["Strike"] < current_price)
            ]
            .sort_values("攻防強度", ascending=False)
        )

        if not upper_call_strength_df.empty:
            strongest_upper_call = upper_call_strength_df.iloc[0]
            strongest_upper_call_strike = strongest_upper_call["Strike"]
            strongest_upper_call_change = strongest_upper_call["OI_change"]
            strongest_upper_call_strength = strongest_upper_call["攻防強度"]
        else:
            strongest_upper_call_strike = None
            strongest_upper_call_change = 0
            strongest_upper_call_strength = 0

        if not lower_put_strength_df.empty:
            strongest_lower_put = lower_put_strength_df.iloc[0]
            strongest_lower_put_strike = strongest_lower_put["Strike"]
            strongest_lower_put_change = strongest_lower_put["OI_change"]
            strongest_lower_put_strength = strongest_lower_put["攻防強度"]
        else:
            strongest_lower_put_strike = None
            strongest_lower_put_change = 0
            strongest_lower_put_strength = 0

        strength_col1, strength_col2 = st.columns(2)

        with strength_col1:
            if strongest_lower_put_strike is not None:
                st.metric(
                    "下側Put 最強攻防",
                    f"{strongest_lower_put_strike:,.0f}円",
                    f"+{strongest_lower_put_change:,.0f}枚",
                )
                st.caption(
                    f"攻防強度：{strongest_lower_put_strength:,.1f}"
                )

        with strength_col2:
            if strongest_upper_call_strike is not None:
                st.metric(
                    "上側Call 最強攻防",
                    f"{strongest_upper_call_strike:,.0f}円",
                    f"+{strongest_upper_call_change:,.0f}枚",
                )
                st.caption(
                    f"攻防強度：{strongest_upper_call_strength:,.1f}"
                )

        st.markdown("### ⚔️ 直近攻防判定")

        battle_strength_total = (
            strongest_lower_put_strength
            + strongest_upper_call_strength
        )

        if battle_strength_total > 0:
            put_strength_share = (
                strongest_lower_put_strength
                / battle_strength_total
                * 100
            )
            call_strength_share = 100 - put_strength_share
        else:
            put_strength_share = 50.0
            call_strength_share = 50.0

        strength_difference = abs(
            call_strength_share
            - put_strength_share
        )

        if strength_difference <= 10:
            battle_judgment = "ほぼ均衡"
            battle_message = (
                "直近のPut側とCall側の攻防強度は拮抗しています。"
                "現在値は上下の攻防ラインに挟まれている状態です。"
            )

        elif call_strength_share > put_strength_share:
            battle_judgment = "上値抵抗優勢"
            battle_message = (
                "直近ではCall側の攻防強度が優勢です。"
                "上側の価格帯がより強く意識される可能性があります。"
            )

        else:
            battle_judgment = "下値支持優勢"
            battle_message = (
                "直近ではPut側の攻防強度が優勢です。"
                "下側の価格帯がより強く意識される可能性があります。"
            )

        battle_judge_col1, battle_judge_col2, battle_judge_col3 = st.columns(3)

        with battle_judge_col1:
            st.metric(
                "Put側攻防比率",
                f"{put_strength_share:.1f}%",
            )

        with battle_judge_col2:
            st.metric(
                "直近攻防判定",
                battle_judgment,
            )

        with battle_judge_col3:
            st.metric(
                "Call側攻防比率",
                f"{call_strength_share:.1f}%",
            )

        st.progress(int(call_strength_share))

        st.info(battle_message)

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

        battle_range_text = (
            f"{nearest_put_strike:,.0f}円 ～ {nearest_call_strike:,.0f}円"
            if (
                nearest_put_strike is not None
                and nearest_call_strike is not None
            )
            else "データなし"
        )

        summary_placeholder.info(
            f"⭐ 状態判定：{result['market_judgment']} "
            f"｜ 状態スコア：{result['total_score']:.1f}点 "
            f"｜ 短期補正：{flow_score_adjustment:+.1f}点 "
            f"｜ 短期総合：{adjusted_total_score:.1f}点 "
            f"｜ 短期判定：{adjusted_market_judgment} "   
            f"｜ 判定差：{judgment_gap_signal} "         
            f"｜ 🧭 状態×変化：{state_change_interpretation} "
            f"｜ 🔄 前日比：{flow_change_judgment} "
            f"（Call {call_share_change:+.1f}pt） "
            f"｜ ⚔ 直近攻防：{battle_range_text}"
        )

        history_row = pd.DataFrame([
            {
                "Date": data_date.strftime("%Y-%m-%d"),
                "CurrentPrice": result["current_price"],
                "StateScore": result["total_score"],
                "FlowAdjustment": flow_score_adjustment,
                "AdjustedScore": adjusted_total_score,
                "StateJudgment": result["market_judgment"],
                "AdjustedJudgment": adjusted_market_judgment,
                "CallShareChange": call_share_change,
                "FlowSignal": total_flow_signal,
                "JudgmentGap": judgment_gap_signal,
            }
        ])

        gas_url = st.secrets["GAS_URL"]

        test_payload = history_row.iloc[0].to_dict()

        response = requests.post(
            gas_url,
            json=test_payload,
            timeout=20,
        )

        history_file = "nikkei225_option_history.csv"

        history_row.to_csv(
            history_file,
            index=False,
            encoding="utf-8-sig",
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

        with st.expander("🔧 開発者向けデータ"):
            st.markdown("#### 📋 取得データの先頭5行")

            st.dataframe(
                option_df.head(),
                width="stretch",
                hide_index=True,
            )

            st.markdown("#### 🔎 列名一覧")

            st.write(option_df.columns.tolist())
    except requests.exceptions.RequestException as e:
        st.error(
            f"J-Quantsへの接続に失敗しました：{e}"
        )

    except Exception as e:
        st.error(
            f"データ処理中にエラーが発生しました：{e}"
        )

    # ========================================
    # Google Sheets 履歴読み込みテスト
    # ========================================

    st.markdown("### 📚 Google Sheets 履歴読み込みテスト")

    try:
        gas_url = st.secrets["GAS_URL"]

        history_response = requests.get(
            gas_url,
            timeout=20,
        )

        history_response.raise_for_status()
        history_json = history_response.json()

        if history_json.get("status") == "success":
            sheet_history = pd.DataFrame(history_json.get("data", []))

            st.success("Google Sheetsから履歴を取得できました")
            st.dataframe(sheet_history, width="stretch")

        else:
            st.error(f"履歴取得エラー: {history_json}")

    except Exception as e:
        st.error(f"Google Sheets履歴の読み込みに失敗しました: {e}")        
