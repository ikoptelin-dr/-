"""Вежливый HTTP-клиент для адаптеров: ограничение частоты по хосту, повторы с паузой, Retry-After,
различение «закрыто политикой сети» и «ошибка площадки». Сеть подменяется в тестах через transport."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlparse

USER_AGENT = "ProbaIntelligenceEngine/0.2 (research prototype; contact: repository owner)"


class SourceBlocked(Exception):
    """Источник недоступен по причине, которую нельзя обходить: сетевая политика, нет ключа, отказ в доступе."""


class SourceError(Exception):
    """Временная или неизвестная ошибка площадки после исчерпания повторов."""


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


Transport = Callable[[str, str, dict[str, str], bytes | None, float], Response]


def urllib_transport(method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float) -> Response:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return Response(r.status, {k.lower(): v for k, v in r.headers.items()}, r.read())
    except urllib.error.HTTPError as e:
        return Response(e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read() or b"")
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "403" in reason or "Tunnel connection failed" in reason or "CONNECT" in reason:
            raise SourceBlocked(f"сетевая политика окружения не пускает к {urlparse(url).hostname}: {reason}") from e
        raise SourceError(f"сеть недоступна: {reason}") from e


class HttpClient:
    def __init__(
        self,
        transport: Transport = urllib_transport,
        min_interval_s: float = 2.0,
        max_retries: int = 3,
        timeout_s: float = 30.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.transport = transport
        self.min_interval_s = min_interval_s
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self.sleep = sleep
        self.clock = clock
        self._last: dict[str, float] = {}
        self.requests_made = 0

    def _throttle(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            wait = self.min_interval_s - (self.clock() - last)
            if wait > 0:
                self.sleep(wait)
        self._last[host] = self.clock()

    def request(self, method: str, url: str, headers: dict[str, str] | None = None, body: bytes | None = None) -> Response:
        host = urlparse(url).hostname or ""
        hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}
        delay = self.min_interval_s
        for attempt in range(self.max_retries + 1):
            self._throttle(host)
            self.requests_made += 1
            resp = self.transport(method, url, hdrs, body, self.timeout_s)
            if resp.status in (401, 403):
                raise SourceBlocked(f"{host} ответил {resp.status}: нет доступа (ключ, права или условия площадки)")
            if resp.status == 429 or resp.status >= 500:
                if attempt == self.max_retries:
                    raise SourceError(f"{host}: {resp.status} после {attempt + 1} попыток")
                retry_after = resp.headers.get("retry-after")
                pause = float(retry_after) if retry_after and retry_after.isdigit() else delay
                self.sleep(pause)
                delay *= 2
                continue
            return resp
        raise SourceError(f"{host}: исчерпаны повторы")  # pragma: no cover

    def get_json(self, url: str, headers: dict[str, str] | None = None) -> Any:
        resp = self.request("GET", url, headers)
        if resp.status != 200:
            raise SourceError(f"{urlparse(url).hostname}: статус {resp.status}")
        return resp.json()
