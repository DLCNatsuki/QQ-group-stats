# -*- coding: utf-8 -*-
"""OneBot v11 HTTP 客户端：只封装统计需要的三个接口。

配合 NapCat / SnowLuma 使用（它们的 HTTP 服务默认 3000 端口）。
"""

from __future__ import annotations

import time
from typing import Any, Callable, Iterator

import requests


class OneBotError(RuntimeError):
    pass


class OneBotClient:
    def __init__(self, base_url: str, token: str = "", timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.timeout = timeout
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    # ---------------------------------------------------------------- 基础

    def call(self, action: str, **params: Any) -> Any:
        url = f"{self.base_url}/{action}"
        try:
            resp = self.session.post(url, json=params or {}, timeout=self.timeout)
        except requests.RequestException as exc:
            raise OneBotError(f"连接失败：{exc}") from exc

        if resp.status_code == 401:
            raise OneBotError("Token 不对（HTTP 401）")
        if resp.status_code >= 400:
            raise OneBotError(f"HTTP {resp.status_code}：{resp.text[:200]}")

        try:
            payload = resp.json()
        except ValueError as exc:
            raise OneBotError(f"返回的不是 JSON：{resp.text[:200]}") from exc

        if payload.get("status") not in (None, "ok"):
            raise OneBotError(f"接口返回异常：{payload}")
        return payload.get("data")

    # ---------------------------------------------------------------- 接口

    def get_group_list(self) -> list[dict]:
        data = self.call("get_group_list")
        return sorted(data or [], key=lambda g: g.get("group_name", ""))

    def get_group_member_count(self, group_id: int) -> int:
        data = self.call("get_group_member_list", group_id=group_id)
        return len(data or [])

    def get_group_msg_history(self, group_id: int, count: int = 100,
                              message_seq: int | None = None) -> list[dict]:
        params: dict[str, Any] = {"group_id": group_id, "count": count}
        if message_seq:
            params["message_seq"] = message_seq
        data = self.call("get_group_msg_history", **params)
        if isinstance(data, dict):
            return data.get("messages") or []
        return data or []

    # ---------------------------------------------------------------- 翻页

    def iter_messages(self, group_id: int, start_ts: float, end_ts: float,
                      page_size: int = 100, max_pages: int = 500,
                      progress: Callable[[int, float], None] | None = None
                      ) -> Iterator[dict]:
        """从最新往旧翻，直到早于 start_ts 或没有更多。"""
        seq: int | None = 0
        page = 0
        seen: set = set()

        while page < max_pages:
            batch = self.get_group_msg_history(group_id, page_size, seq)
            if not batch:
                return

            # 接口返回可能是升序也可能是降序，统一按时间排序
            batch.sort(key=lambda m: m.get("time", 0))
            oldest = batch[0].get("time", 0)
            newest = batch[-1].get("time", 0)

            for msg in batch:
                key = (msg.get("message_id"), msg.get("time"))
                if key in seen:
                    continue
                seen.add(key)
                t = msg.get("time", 0)
                if start_ts <= t <= end_ts:
                    yield msg

            page += 1
            if progress:
                progress(page, oldest)

            # 已经翻到比开始时间更早，停
            if oldest and oldest < start_ts:
                return

            # 计算下一页的 seq：取本页最小 seq 继续往前
            seqs = [m.get("message_seq") or m.get("real_seq") or 0 for m in batch]
            seqs = [s for s in seqs if s]
            if not seqs:
                return
            next_seq = min(seqs)
            if next_seq == seq:
                return  # 防止死循环
            seq = next_seq

            if newest <= start_ts:
                return
