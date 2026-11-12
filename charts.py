# -*- coding: utf-8 -*-
"""图表：返回 matplotlib 的 Figure，由界面嵌入显示。"""

from __future__ import annotations

import matplotlib

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

from matplotlib.figure import Figure


def fig_daily(result: dict) -> Figure:
    days = result["by_day"]
    fig = Figure(figsize=(6, 3.6), dpi=100)
    ax = fig.add_subplot(111)

    if not days:
        ax.text(0.5, 0.5, "没有数据", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig

    labels = [d for d, _ in days]
    values = [v for _, v in days]
    bars = ax.bar(labels, values, color="#4ade80", edgecolor="#16a34a")

    ax.set_title("每日消息量")
    ax.set_ylabel("条数")
    ax.tick_params(axis="x", rotation=45 if len(labels) > 6 else 0, labelsize=8)
    ax.grid(axis="y", alpha=0.25)

    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v, str(v),
                ha="center", va="bottom", fontsize=7)

    fig.tight_layout()
    return fig


def fig_top(result: dict) -> Figure:
    top = result["top_speakers"]
    fig = Figure(figsize=(6, 3.6), dpi=100)
    ax = fig.add_subplot(111)

    if not top:
        ax.text(0.5, 0.5, "没有数据", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig

    names = [n for n, _ in top][::-1]
    counts = [c for _, c in top][::-1]
    bars = ax.barh(names, counts, color="#60a5fa", edgecolor="#2563eb")

    ax.set_title("发言排行 Top 10")
    ax.set_xlabel("条数")
    ax.grid(axis="x", alpha=0.25)

    for bar, c in zip(bars, counts):
        ax.text(c, bar.get_y() + bar.get_height() / 2, f" {c}",
                va="center", fontsize=8)

    fig.tight_layout()
    return fig


def fig_ratio(result: dict) -> Figure:
    active = result["active"]
    silent = max(0, result["member_count"] - active)

    fig = Figure(figsize=(6, 3.6), dpi=100)
    ax = fig.add_subplot(111)

    if result["member_count"] <= 0:
        ax.text(0.5, 0.5, "拿不到群成员数", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return fig

    ax.pie([active, silent],
           labels=[f"发言 {active} 人", f"未发言 {silent} 人"],
           colors=["#f59e0b", "#334155"],
           autopct="%1.1f%%",
           startangle=90,
           textprops={"fontsize": 10})
    ax.set_title(f"活跃比 {result['ratio'] * 100:.1f}%")
    fig.tight_layout()
    return fig
