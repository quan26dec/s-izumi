# ============================================================
# 日経225需給分析 Ver.4
# 分析エンジン
# ============================================================

from datetime import datetime

import pandas as pd


def calculate_market_analysis(
    option_df: pd.DataFrame,
    analysis_days: int,
) -> dict:
    """
    日経225需給分析を実行し、結果を辞書形式で返します。

    現在は移植確認用の仮データです。
    次の段階でJ-Quantsの実データへ置き換えます。
    """

    # --------------------------------------------------------
    # 仮の分析データ
    # --------------------------------------------------------

    current_price = option_df["UnderPx"].dropna().iloc[0]
    call_center = 72540
    put_center = 53580

    call_distance = abs(
        call_center - current_price
    )

    put_distance = abs(
        current_price - put_center
    )

    center_width = abs(
        call_center - put_center
    )

    if center_width == 0:
        position_ratio = 50.0
    else:
        position_ratio = (
            (current_price - put_center)
            / center_width
            * 100
        )

    if call_distance < put_distance:
        nearest_center = "Call側"
    elif put_distance < call_distance:
        nearest_center = "Put側"
    else:
        nearest_center = "中立"

    # 仮の総合需給スコア
    total_score = 42.8

    if total_score >= 70:
        market_judgment = "強気"
        stars = "★★★★★"

    elif total_score >= 60:
        market_judgment = "やや強気"
        stars = "★★★★☆"

    elif total_score >= 40:
        market_judgment = "中立"
        stars = "★★★☆☆"

    elif total_score >= 30:
        market_judgment = "やや弱気"
        stars = "★★☆☆☆"

    else:
        market_judgment = "弱気"
        stars = "★☆☆☆☆"

    # --------------------------------------------------------
    # 表示用の距離分析表
    # --------------------------------------------------------

    distance_df = pd.DataFrame({
        "項目": [
            "現在値",
            "Call重心",
            "Put重心",
            "Call重心までの距離",
            "Put重心までの距離",
            "Put→Call間の現在値位置",
            "近い建玉重心"
        ],
        "結果": [
            f"{current_price:,.0f}円",
            f"{call_center:,.0f}円",
            f"{put_center:,.0f}円",
            f"{call_distance:,.0f}円",
            f"{put_distance:,.0f}円",
            f"{position_ratio:.1f}%",
            nearest_center
        ]
    })

    # --------------------------------------------------------
    # app.pyへ返す
    # --------------------------------------------------------

    return {
        "analysis_datetime": datetime.now(),
        "analysis_days": analysis_days,
        "current_price": current_price,
        "call_center": call_center,
        "put_center": put_center,
        "call_distance": call_distance,
        "put_distance": put_distance,
        "position_ratio": position_ratio,
        "nearest_center": nearest_center,
        "total_score": total_score,
        "market_judgment": market_judgment,
        "stars": stars,
        "distance_df": distance_df
    }
