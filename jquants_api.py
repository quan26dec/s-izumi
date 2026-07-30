# ============================================================
# 日経225需給分析 Ver.4
# J-Quants API データ取得
# ============================================================

from datetime import datetime

import pandas as pd
import requests


BASE_URL = "https://api.jquants.com/v2"


class JQuantsAPIError(Exception):
    """J-Quants API取得時の独自エラーです。"""


def normalize_date(target_date) -> str:
    """
    日付をJ-Quants用の YYYYMMDD 形式へ変換します。

    使用できる例：
    2026-07-30
    20260730
    datetime型
    """

    if isinstance(target_date, datetime):
        return target_date.strftime("%Y%m%d")

    date_text = str(target_date).strip()

    date_text = (
        date_text
        .replace("-", "")
        .replace("/", "")
    )

    if len(date_text) != 8 or not date_text.isdigit():
        raise ValueError(
            "日付は YYYY-MM-DD または YYYYMMDD で指定してください。"
        )

    return date_text


def fetch_options_by_date(
    api_key: str,
    target_date,
) -> pd.DataFrame:
    """
    指定日のオプションデータをJ-Quantsから取得します。

    Parameters
    ----------
    api_key:
        Streamlit Secretsから受け取ったJ-Quants APIキー

    target_date:
        取得日。YYYY-MM-DDまたはYYYYMMDD

    Returns
    -------
    pandas.DataFrame
        指定日のオプションデータ
    """

    if not api_key:
        raise ValueError(
            "J-Quants APIキーが設定されていません。"
        )

    date_value = normalize_date(target_date)

    url = f"{BASE_URL}/derivatives/bars/daily/options/225"

    headers = {
        "x-api-key": api_key
    }

    params = {
        "date": date_value
    }

    all_records = []
    pagination_key = None

    while True:

        request_params = params.copy()

        if pagination_key:
            request_params["pagination_key"] = pagination_key

        try:
            response = requests.get(
                url,
                headers=headers,
                params=request_params,
                timeout=30
            )

            response.raise_for_status()

        except requests.exceptions.Timeout as exc:
            raise JQuantsAPIError(
                "J-Quants APIへの接続がタイムアウトしました。"
            ) from exc

        except requests.exceptions.HTTPError as exc:

            status_code = response.status_code

            if status_code == 401:
                message = (
                    "認証に失敗しました。"
                    "Streamlit SecretsのAPIキーを確認してください。"
                )

            elif status_code == 403:
                message = (
                    "このデータを取得する権限がありません。"
                    "J-Quantsの契約プランを確認してください。"
                )

            elif status_code == 404:
                message = (
                    "J-Quantsの取得先が見つかりませんでした。"
                )

            elif status_code == 429:
                message = (
                    "APIの利用回数上限に達しました。"
                    "少し時間を空けて再実行してください。"
                )

            else:
                message = (
                    f"J-Quants APIでHTTPエラーが発生しました。"
                    f"ステータスコード：{status_code}"
                )

            raise JQuantsAPIError(message) from exc

        except requests.exceptions.RequestException as exc:
            raise JQuantsAPIError(
                "J-Quants APIへの接続に失敗しました。"
            ) from exc

        response_data = response.json()

        records = response_data.get("options", [])

        if not records:
            break

        all_records.extend(records)

        pagination_key = response_data.get(
            "pagination_key"
        )

        if not pagination_key:
            break

    options_df = pd.DataFrame(all_records)

    if options_df.empty:
        raise JQuantsAPIError(
            f"{date_value}のオプションデータを取得できませんでした。"
            "休場日またはデータ未更新の可能性があります。"
        )

    return options_df
