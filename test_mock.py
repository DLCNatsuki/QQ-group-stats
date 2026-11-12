# -*- coding: utf-8 -*-
"""端到端测试：起一个假的 OneBot HTTP 服务器，验证翻页与统计。"""

import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import stats
from onebot import OneBotClient

TZ = timezone(timedelta(hours=8))
BASE = datetime(2026, 11, 1, 12, 0, tzinfo=TZ).timestamp()

# 10 条消息，跨 3 天，3 个人轮流发
MSGS = []
for i in range(10):
    sender_id = ["1001", "1002", "1003"][i % 3]
    MSGS.append({
        "message_id": 1000 + i,
        "message_seq": 1000 + i,
        "time": int(BASE + i * 3600 * 6),   # 每条间隔 8 小时，跨 3 天
        "user_id": sender_id,
        "sender": {"user_id": sender_id, "nickname": f"用户{sender_id[-1]}"},
        "message": [{"type": "text", "data": {"text": f"消息{i}"}}],
    })

MEMBERS = [{"user_id": 1000 + i, "nickname": f"m{i}"} for i in range(10)]
GROUPS = [{"group_id": 1001, "group_name": "测试群", "member_count": 10}]

CALLS = {"history": 0}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        action = self.path.strip("/")

        if action == "get_group_list":
            data = GROUPS
        elif action == "get_group_member_list":
            data = MEMBERS
        elif action == "get_group_msg_history":
            CALLS["history"] += 1
            seq = body.get("message_seq") or 0
            count = body.get("count", 3)
            pool = [m for m in MSGS if seq == 0 or m["message_seq"] < seq]
            data = {"messages": pool[-count:]}
        else:
            data = None

        payload = json.dumps({"status": "ok", "retcode": 0, "data": data}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # 安静
        pass


def main() -> None:
    server = HTTPServer(("127.0.0.1", 18080), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    client = OneBotClient("http://127.0.0.1:18080")

    groups = client.get_group_list()
    assert groups and groups[0]["group_id"] == 1001, groups
    print("✓ 群列表:", groups[0]["group_name"])

    members = client.get_group_member_count(1001)
    assert members == 10, members
    print("✓ 群成员数:", members)

    start, _ = stats.date_range("2026-11-01", "2026-11-01")
    _, end = stats.date_range("2026-11-03", "2026-11-03")
    msgs = list(client.iter_messages(1001, start, end, page_size=3))
    print(f"✓ 拉取消息: {len(msgs)} 条，调用接口 {CALLS['history']} 次")
    assert len(msgs) == 10, [m["message_id"] for m in msgs]

    result = stats.summarize(msgs, members)
    print("✓ 统计结果:")
    print(stats.summary_text(result, "2026-11-01", "2026-11-03"))
    assert result["total"] == 10
    assert result["active"] == 3
    assert result["ratio"] == 3 / 10
    assert len(result["by_day"]) == 3, result["by_day"]
    assert result["top_speakers"][0][1] in (3, 4)

    server.shutdown()
    print("\n全部通过 ✅")


if __name__ == "__main__":
    main()

