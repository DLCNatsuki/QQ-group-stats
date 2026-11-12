# -*- coding: utf-8 -*-
"""QQ 群聊统计工具 —— 图形界面（Tkinter）。

依赖本地 OneBot 协议端（NapCat / SnowLuma）提供 HTTP 接口。
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import charts
import stats
from onebot import OneBotClient, OneBotError

DEFAULT_URL = "http://127.0.0.1:3000"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QQ 群聊统计工具")
        self.geometry("900x700")
        self.minsize(820, 640)

        self.client: OneBotClient | None = None
        self.groups: list[dict] = []
        self.queue: queue.Queue = queue.Queue()
        self.running = False

        self._build_ui()
        self.after(100, self._poll_queue)

    # ---------------------------------------------------------------- UI

    def _build_ui(self) -> None:
        pad = {"padx": 6, "pady": 4}

        top = ttk.LabelFrame(self, text="1. 连接协议端（NapCat / SnowLuma）")
        top.pack(fill="x", **pad)

        ttk.Label(top, text="地址").grid(row=0, column=0, sticky="e")
        self.url_var = tk.StringVar(value=DEFAULT_URL)
        ttk.Entry(top, textvariable=self.url_var, width=28).grid(row=0, column=1, sticky="w")

        ttk.Label(top, text="Token").grid(row=0, column=2, sticky="e")
        self.token_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.token_var, width=20, show="*").grid(row=0, column=3, sticky="w")

        self.btn_connect = ttk.Button(top, text="连接", command=self.on_connect)
        self.btn_connect.grid(row=0, column=4, padx=8)

        self.status_var = tk.StringVar(value="未连接")
        ttk.Label(top, textvariable=self.status_var, foreground="#666").grid(
            row=0, column=5, sticky="w")

        mid = ttk.LabelFrame(self, text="2. 选择群与时间范围")
        mid.pack(fill="x", **pad)

        ttk.Label(mid, text="群").grid(row=0, column=0, sticky="e")
        self.group_var = tk.StringVar()
        self.group_box = ttk.Combobox(mid, textvariable=self.group_var, width=40, state="readonly")
        self.group_box.grid(row=0, column=1, columnspan=3, sticky="w")

        ttk.Label(mid, text="开始日期").grid(row=1, column=0, sticky="e")
        self.start_var = tk.StringVar(value=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
        ttk.Entry(mid, textvariable=self.start_var, width=14).grid(row=1, column=1, sticky="w")

        ttk.Label(mid, text="结束日期").grid(row=1, column=2, sticky="e")
        self.end_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(mid, textvariable=self.end_var, width=14).grid(row=1, column=3, sticky="w")

        ttk.Label(mid, text="格式 YYYY-MM-DD，含首尾两天",
                  foreground="#888").grid(row=2, column=1, columnspan=3, sticky="w")

        self.btn_run = ttk.Button(mid, text="开始统计", command=self.on_run, state="disabled")
        self.btn_run.grid(row=1, column=4, padx=8)

        self.progress_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.progress_var, foreground="#2563eb").pack(anchor="w", padx=12)

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

    # ---------------------------------------------------------------- 工具

    def set_summary(self, text: str) -> None:
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

    def _poll_queue(self) -> None:
        try:
            while True:
                fn, args = self.queue.get_nowait()
                fn(*args)
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)

    def post(self, fn, *args) -> None:
        self.queue.put((fn, args))

    # ---------------------------------------------------------------- 事件

    def on_connect(self) -> None:
        url = self.url_var.get().strip()
        token = self.token_var.get().strip()
        if not url.startswith("http"):
            messagebox.showwarning("地址不对", "地址要以 http:// 开头，例如 http://127.0.0.1:3000")
            return

        self.status_var.set("连接中…")
        self.btn_connect.configure(state="disabled")

        def work():
            try:
                client = OneBotClient(url, token)
                groups = client.get_group_list()
                self.post(self._connected, client, groups)
            except Exception as exc:  # noqa: BLE001
                self.post(self._connect_failed, str(exc))

        threading.Thread(target=work, daemon=True).start()

    def _connected(self, client: OneBotClient, groups: list[dict]) -> None:
        self.client = client
        self.groups = groups
        self.btn_connect.configure(state="normal")

        if not groups:
            self.status_var.set("已连接，但没有群")
            messagebox.showinfo("提示", "这个 QQ 号没有加入任何群。")
            return

        self.status_var.set(f"已连接，共 {len(groups)} 个群")
        self.group_box["values"] = [
            f"{g.get('group_name', '?')}（{g.get('group_id')}）" for g in groups
        ]
        self.group_box.current(0)
        self.btn_run.configure(state="normal")

    def _connect_failed(self, msg: str) -> None:
        self.btn_connect.configure(state="normal")
        self.status_var.set("连接失败")
        messagebox.showerror("连接失败", msg + "\n\n检查：\n"
                            "1. NapCat 是否启动\n"
                            "2. HTTP 服务端口是否为 3000\n"
                            "3. Token 是否一致")

    def on_run(self) -> None:
        if not self.client or self.running:
            return
        idx = self.group_box.current()
        if idx < 0:
            messagebox.showwarning("没选群", "请先选择一个群")
            return

        group = self.groups[idx]
        gid = int(group["group_id"])

        try:
            start_ts, _ = stats.date_range(self.start_var.get(), self.start_var.get())
            _, end_ts = stats.date_range(self.end_var.get(), self.end_var.get())
        except ValueError:
            messagebox.showerror("日期格式错", "请用 YYYY-MM-DD，例如 2026-11-01")
            return
        if start_ts > end_ts:
            messagebox.showerror("日期范围错", "开始日期不能晚于结束日期")
            return

        self.running = True
        self.btn_run.configure(state="disabled")
        self.progress_var.set("正在拉取消息…")

        def work():
            try:
                members = self.client.get_group_member_count(gid)
                msgs = list(self.client.iter_messages(
                    gid, start_ts, end_ts,
                    progress=lambda page, oldest: self.post(
                        self.progress_var.set, f"已拉取 {page} 页…"),
                ))
                result = stats.summarize(msgs, members)
                self.post(self._show_result, result, group)
            except Exception as exc:  # noqa: BLE001
                self.post(self._run_failed, str(exc))

        threading.Thread(target=work, daemon=True).start()

    def _run_failed(self, msg: str) -> None:
        self.running = False
        self.btn_run.configure(state="normal")
        self.progress_var.set("")
        messagebox.showerror("统计失败", msg)

    def _show_result(self, result: dict, group: dict) -> None:
        self.running = False
        self.btn_run.configure(state="normal")
        self.progress_var.set(f"完成：{result['total']} 条消息")

        self.show_figure(self.tab_daily, charts.fig_daily(result))
        self.show_figure(self.tab_top, charts.fig_top(result))
        self.show_figure(self.tab_ratio, charts.fig_ratio(result))

        text = stats.summary_text(result, self.start_var.get(), self.end_var.get())
        text = f"群：{group.get('group_name', '')}\n" + text
        self.set_summary(text)


if __name__ == "__main__":
    App().mainloop()
