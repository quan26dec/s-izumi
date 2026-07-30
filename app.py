# ============================================================
# 日経225需給分析 Ver.4
# Streamlitアプリ本体
# ============================================================

import streamlit as st

from analysis import calculate_market_analysis
from jquants_api import fetch_options_by_date

# ============================================================
# 1. ページ設定
# ============================================================

st.set_page_config(
    page_title="日経225需給分析 Ver.4",
    page_icon="📈",
    layout="wide"
)


# ============================================================
# 2. タイトル
# ============================================================

st.title("📈 日経225需給分析 Ver.4")

# J-Quants APIキー取得
api_key = st.secrets["JQUANTS_API_KEY"]

st.caption(
    "J-Quantsのオプションデータを使って、"
    "日経225の需給を分析します。"
)


# ============================================================
# 3. サイドバー
# ============================================================

with st.sidebar:

    st.header("⚙️ 分析設定")

    analysis_days = st.selectbox(
        "分析営業日数",
        options=[5, 10, 20],
        index=0
    )

    st.write(
        f"現在の設定：直近{analysis_days}営業日"
    )

    st.divider()

    st.info(
        "現在は分析エンジンの移植確認中です。"
        "次の段階でJ-Quantsへ接続します。"
    )


# ============================================================
# 4. 分析開始ボタン
# ============================================================

st.subheader("需給分析")

start_analysis = st.button(
    "📊 分析を開始する",
    type="primary",
    use_container_width=True
)


# ============================================================
# 5. 分析実行
# ============================================================

if start_analysis:

    with st.spinner(
        "日経225オプションの需給を分析しています..."
    ):
    try:
    option_df = fetch_options_by_date(
        api_key=api_key,
        target_date="20260730"
    )

    st.success(
        f"J-Quants接続成功！ "
        f"{len(option_df)}件取得しました。"
    )

except Exception as e:

    st.error(f"J-Quants接続エラー：{e}")

    st.stop()
        result = calculate_market_analysis(
            analysis_days=analysis_days
        )

    st.success(
        "analysis.pyの分析処理を正常に実行しました！"
    )

    # --------------------------------------------------------
    # 基本指標
    # --------------------------------------------------------

    st.subheader("📊 最新の需給指標")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="現在値",
            value=f"{result['current_price']:,.0f}円"
        )

    with col2:
        st.metric(
            label="Call重心",
            value=f"{result['call_center']:,.0f}円",
            delta=(
                f"現在値から "
                f"{result['call_distance']:,.0f}円"
            )
        )

    with col3:
        st.metric(
            label="Put重心",
            value=f"{result['put_center']:,.0f}円",
            delta=(
                f"現在値から "
                f"{result['put_distance']:,.0f}円"
            )
        )

    # --------------------------------------------------------
    # 総合判定
    # --------------------------------------------------------

    st.subheader("⭐ 総合需給判定")

    judgment_col1, judgment_col2 = st.columns(2)

    with judgment_col1:
        st.metric(
            label="総合需給スコア",
            value=f"{result['total_score']:.1f}点"
        )

    with judgment_col2:
        st.metric(
            label="需給判定",
            value=result["market_judgment"]
        )

    st.write(
        f"評価：**{result['stars']}**"
    )

    # --------------------------------------------------------
    # 距離分析
    # --------------------------------------------------------

    st.subheader("📍 現在値と建玉重心の距離分析")

    st.dataframe(
        result["distance_df"],
        use_container_width=True,
        hide_index=True
    )

    st.info(
        f"現在値はPut重心からCall重心方向へ"
        f"{result['position_ratio']:.1f}%の位置です。"
        f"現在は「{result['nearest_center']}」に近い状態です。"
    )

    # --------------------------------------------------------
    # 実行情報
    # --------------------------------------------------------

    with st.expander("実行情報を見る"):

        st.write(
            "分析日時：",
            result["analysis_datetime"].strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        st.write(
            "分析期間：",
            f"{result['analysis_days']}営業日"
        )

        st.write(
            "データ状態：",
            "移植確認用の仮データ"
        )

else:

    st.info(
        "「分析を開始する」ボタンを押してください。"
    )


# ============================================================
# 6. フッター
# ============================================================

st.divider()

st.caption(
    "※現在は移植確認用の仮データを使用しています。"
    "分析結果は将来の値動きを保証するものではありません。"
)
