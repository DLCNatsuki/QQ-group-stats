# -*- coding: utf-8 -*-
"""QQ 群聊统计 —— 离线版（读取导出的聊天记录，不需要任何服务）。

用法：
    1. 在 PC QQ 里导出群消息记录为 .txt
       消息管理器 → 选中群 → 右键「导出消息记录」→ 选 txt
    2. 运行本程序，选文件、填群人数、选日期
"""

from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import charts
import local_reader
import stats


class OfflineApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QQ 群聊统计工具 · 离线版")
        self.geometry("900x700")
        self.minsize(820, 640)

        self.messages: list[dict] = []
        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 6, "pady": 4}

        top = ttk.LabelFrame(self, text="1. 选择导出的聊天记录（.txt）")
        top.pack(fill="x", **pad)

        self.path_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.path_var, width=60).grid(row=0, column=0, padx=6, pady=6, sticky="we")
        ttk.Button(top, text="浏览…", command=self.on_pick).grid(row=0, column=1, padx=6)
        top.columnconfigure(0, weight=1)

        ttk.Label(top, text="怎么导出：QQ 消息管理器 → 选中群 → 右键「导出消息记录」→ 选 .txt",
                  foreground="#888").grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6))

        mid = ttk.LabelFrame(self, text="2. 统计条件")
        mid.pack(fill="x", **pad)

        ttk.Label(mid, text="群人数").grid(row=0, column=0, sticky="e")
        self.members_var = tk.StringVar(value="0")
        ttk.Spinbox(mid, from_=0, to=5000, textvariable=self.members_var, width=8).grid(row=0, column=1, sticky="w")
        ttk.Label(mid, text="（用于算活跃比，不知道就填 0）",
                  foreground="#888").grid(row=0, column=2, sticky="w")

        ttk.Label(mid, text="开始日期").grid(row=1, column=0, sticky="e")
        self.start_var = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
        ttk.Entry(mid, textvariable=self.start_var, width=14).grid(row=1, column=1, sticky="w")

        ttk.Label(mid, text="结束日期").grid(row=1, column=2, sticky="e")
        self.end_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(mid, textvariable=self.end_var, width=14).grid(row=1, column=3, sticky="w")

        ttk.Button(mid, text="开始统计", command=self.on_run).grid(row=1, column=4, padx=10)

        self.status_var = tk.StringVar(value="等待选择文件")
        ttk.Label(self, textvariable=self.status_var, foreground="#2563eb").pack(anchor="w", padx=12)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=6, pady=4)
        self.tab_daily = ttk.Frame(self.nb)
        self.tab_top = ttk.Frame(self.nb)
        self.tab_ratio = ttk.Frame(self.nb)
        self.nb.add(self.tab_daily, text="每日趋势")
        self.nb.add(self.tab_top, text="发言排行")
        self.nb.add(self.tab_ratio, text="活跃比")

        self.summary = tk.Text(self, height=7, wrap="word")
        self.summary.pack(fill="x", padx=6, pady=(0, 6))
        self.summary.configure(state="disabled")

    def on_pick(self) -> None:
        path = filedialog.askopenfilename(
            title="选择导出的聊天记录",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return
        self.path_var.set(path)
        try:
            self.messages = local_reader.parse_text_export(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("读取失败", str(exc))
            return
        self.status_var.set(f"已读取 {len(self.messages)} 条消息")

    def on_run(self) -> None:
        if not self.messages:
            messagebox.showwarning("没有数据", "先选一个导出的 .txt 文件")
            return

        try:
            start_ts, _ = stats.date_range(self.start_var.get(), self.start_var.get())
            _, end_ts = stats.date_range(self.end_var.get(), self.end_var.get())
        except ValueError:
            messagebox.showerror("日期格式错", "请用 YYYY-MM-DD")
            return

        try:
            total_members = int(self.members_var.get() or 0)
        except ValueError:
            total_members = 0

        picked = [m for m in self.messages if start_ts <= m["time"] <= end_ts]
        if not picked:
            messagebox.showinfo("没有消息", "这个时间段里没有消息，换个日期试试")
            return

        result = stats.summarize(picked, total_members)
        self.status_var.set(f"统计完成：{result['total']} 条消息")

        for tab, fn in ((self.tab_daily, charts.fig_daily),
                        (self.tab_top, charts.fig_top),
                        (self.tab_ratio, charts.fig_ratio)):
            self.show_figure(tab, fn(result))

        text = stats.summary_text(result, self.start_var.get(), self.end_var.get())
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", text)
        self.summary.configure(state="disabled")

    def show_figure(self, tab: ttk.Frame, fig) -> None:
        for child in tab.winfo_children():
            child.destroy()
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


if __name__ == "__main__":
    OfflineApp().mainloop()
