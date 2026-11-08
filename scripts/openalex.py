from __future__ import annotations

import time
from typing import Any

import requests

from . import config


class OpenAlexError(RuntimeError):
    pass


class OpenAlexClient:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.remaining: int | None = None

    def fetch_page(self, params: dict[str, Any]) -> dict[str, Any]:
        request_params = dict(params)
        if config.API_KEY:
            request_params["api_key"] = config.API_KEY
        if config.MAILTO:
            request_params["mailto"] = config.MAILTO

        for attempt in range(config.MAX_RETRIES):
            try:
                response = self.session.get(
                    config.API_BASE, params=request_params, timeout=config.REQUEST_TIMEOUT
                )
            except requests.RequestException as exc:
                if attempt == config.MAX_RETRIES - 1:
                    raise OpenAlexError(f"OpenAlex 网络请求失败: {exc}") from exc
                time.sleep(2 ** (attempt + 1))
                continue

            self._read_rate_limit(response.headers)
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise OpenAlexError("OpenAlex 返回了无法解析的 JSON") from exc

            message = self._message(response)
            if response.status_code == 429:
                if "Plan upgrade required" in message:
                    raise OpenAlexError(f"OpenAlex 需要更高套餐: {message}")
                if attempt < config.MAX_RETRIES - 1:
                    retry_after = response.headers.get("Retry-After", "2")
                    try:
                        delay = max(1, float(retry_after))
                    except ValueError:
                        delay = 2 ** (attempt + 1)
                    time.sleep(delay)
                    continue
                raise OpenAlexError(f"OpenAlex 请求频率或额度受限: {message}")

            if response.status_code in (500, 503) and attempt < config.MAX_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            if response.status_code == 401:
                raise OpenAlexError("OpenAlex 返回 401；请检查 OPENALEX_API_KEY，游标翻页必须配置 Key")
            raise OpenAlexError(f"OpenAlex HTTP {response.status_code}: {message}")

        raise OpenAlexError("OpenAlex 请求重试次数已用尽")

    @staticmethod
    def _message(response: requests.Response) -> str:
        try:
            body = response.json()
            if isinstance(body, dict):
                error = body.get("error")
                message = body.get("message")
                if error or message:
                    return ": ".join(str(part) for part in (error, message) if part)
        except ValueError:
            pass
        return response.text[:500] or response.reason

    def _read_rate_limit(self, headers: requests.structures.CaseInsensitiveDict) -> None:
        value = headers.get("X-RateLimit-Remaining")
        if value is not None:
            try:
                self.remaining = int(value)
            except ValueError:
                self.remaining = None
