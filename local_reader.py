# -*- coding: utf-8 -*-
"""解析 QQ 导出的聊天记录文本。

支持 QQ 消息管理器导出的 .txt，常见格式：

    2026-11-01 12:00:00 昵称(123456)
    消息内容

    2026-11-01 12:00:00 昵称<123456>
    消息内容

也兼容「昵称 123456」不带括号的情况；多行消息会合并。
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

# 2026-11-01 12:00:00 / 2026-11-01 12:00
HEADER_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)\s*$")
# 结尾的 (123456) / <123456> / （123456）
UID_RE = re.compile(r"[<(（]\s*(\d{5,12})\s*[>)）]\s*$")


def read_text(path: str | Path) -> str:
    p = Path(path)
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_text_export(path: str | Path) -> list[dict]:
    """返回 [{time, user_id, sender:{nickname}, text}]。"""
    text = read_text(path)
    lines = text.splitlines()

    messages: list[dict] = []
    cur: dict | None = None

    for line in lines:
        m = HEADER_RE.match(line)
        if m:
            if cur:
                messages.append(cur)

            time_str, tail = m.group(1), m.group(2).strip()
            uid = ""
            um = UID_RE.search(tail)
            if um:
                uid = um.group(1)
                nickname = tail[: um.start()].strip()
            else:
                nickname = tail

            try:
                dt = datetime.strptime(
                    time_str if len(time_str) > 16 else time_str + ":00",
                    "%Y-%m-%d %H:%M:%S")
            except ValueError:
                dt = None

            cur = {
                "time": dt.timestamp() if dt else 0,
                "message_id": len(messages),
                "user_id": uid or nickname,
                "sender": {"user_id": uid, "nickname": nickname or "未知"},
                "text": "",
            }
        elif cur is not None and line.strip():
            cur["text"] = (cur["text"] + "\n" + line).strip()

    if cur:
        messages.append(cur)

    return [m for m in messages if m["time"] > 0]


if __name__ == "__main__":
    import sys

    msgs = parse_text_export(sys.argv[1])
    print(f"解析到 {len(msgs)} 条消息")
    for m in msgs[:5]:
        t = datetime.fromtimestamp(m["time"]).strftime("%Y-%m-%d %H:%M")
        print(f"  {t}  {m['sender']['nickname']}: {m['text'][:30]}")
