# -*- coding: utf-8 -*-
"""统计逻辑：纯函数，方便测试。"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone


def day_key(ts: float, tz_hours: int = 8) -> str:
    tz = timezone(timedelta(hours=tz_hours))
    return datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d")


def sender_of(msg: dict) -> tuple[str, str]:
    """返回 (uid, 显示名)。"""
    sender = msg.get("sender") or {}
    uid = str(msg.get("user_id") or sender.get("user_id") or "")
    name = sender.get("card") or sender.get("nickname") or f"用户{uid}"
    return uid, str(name)


def summarize(messages: list[dict], member_count: int,
              tz_hours: int = 8) -> dict:
    total = len(messages)
    counter: Counter = Counter()
    names: dict[str, str] = {}
    by_day: dict[str, int] = defaultdict(int)

    for msg in messages:
        uid, name = sender_of(msg)
        if not uid:
            continue
        counter[uid] += 1
        names.setdefault(uid, name)
        by_day[day_key(msg.get("time", 0), tz_hours)] += 1

    active = len(counter)
    ratio = (active / member_count) if member_count else 0.0

    top = [(names[uid], cnt) for uid, cnt in counter.most_common(10)]
    days = sorted(by_day.items())

    return {
        "total": total,
        "active": active,
        "member_count": member_count,
        "ratio": ratio,
        "avg_per_active": (total / active) if active else 0.0,
        "top_speakers": top,
        "by_day": days,
        "all_ranked": [(names[uid], cnt) for uid, cnt in counter.most_common()],
    }


def ratio_label(ratio: float) -> str:
    pct = ratio * 100
    if pct >= 60:
        level = "非常活跃"
    elif pct >= 30:
        level = "比较活跃"
    elif pct >= 10:
        level = "一般"
    else:
        level = "比较冷清"
    return f"{pct:.1f}%（{level}）"


def summary_text(result: dict, start: str, end: str) -> str:
    lines = [
        f"统计区间：{start} ~ {end}",
        f"消息总数：{result['total']} 条",
        f"发言人数：{result['active']} / 群成员 {result['member_count']} 人",
        f"活跃比：{ratio_label(result['ratio'])}",
        f"人均发言：{result['avg_per_active']:.1f} 条（按发言者算）",
    ]
    if result["top_speakers"]:
        lines.append("发言最多：" + "、".join(f"{n}({c})" for n, c in result["top_speakers"][:3]))
    return "\n".join(lines)


def date_range(start: str, end: str) -> tuple[float, float]:
    """把 'YYYY-MM-DD' 转成本地时区当天 00:00 ~ 次日 00:00 的时间戳。"""
    def parse(s: str, end_of_day: bool = False) -> float:
        dt = datetime.strptime(s.strip(), "%Y-%m-%d")
        dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
        if end_of_day:
            dt = dt + timedelta(days=1)
        return dt.timestamp()

    return parse(start), parse(end, end_of_day=True)
