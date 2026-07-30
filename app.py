import streamlit as st
import pandas as pd
from datetime import datetime


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
        "J-Quantsの接続情報は、"
        "GitHubではなくStreamlit Secretsに保存します。"
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
# 5. ボタンを押した後の処理
# ============================================================

if start_analysis:

    with st.spinner("日経225オプションを分析しています..."):

        # 現段階では動作確認用の仮データ
        # 次のステップでJ-Quants APIへ置き換える
        sample_data = pd.DataFrame({
            "項目": [
                "分析日時",
                "分析営業日数",
                "J-Quants接続",
                "建玉分析",
                "建玉重心",
                "総合需給スコア"
            ],
            "結果": [
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                f"{analysis_days}営業日",
                "次のステップで接続",
                "移植準備完了",
                "移植準備完了",
                "移植準備完了"
            ]
        })

    st.success("分析処理が正常に実行されました！")

    st.subheader("📋 実行結果")

    st.dataframe(
        sample_data,
        use_container_width=True,
        hide_index=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="現在値",
            value="移植準備中"
        )

    with col2:
        st.metric(
            label="Call重心",
            value="移植準備中"
        )

    with col3:
        st.metric(
            label="Put重心",
            value="移植準備中"
        )

    st.info(
        "次のステップで、ColabのJ-Quantsデータ取得処理を"
        "このボタンへ接続します。"
    )

else:

    st.info(
        "上の「分析を開始する」ボタンを押してください。"
    )


# ============================================================
# 6. フッター
# ============================================================

st.divider()

st.caption(
    "※本アプリの分析結果は投資判断の参考情報であり、"
    "将来の値動きを保証するものではありません。"
)
