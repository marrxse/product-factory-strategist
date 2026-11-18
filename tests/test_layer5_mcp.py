"""MCP-сервер: протокол (initialize, tools/list, tools/call) по stdio и вызов тех же команд, что CLI."""
import json
import os
import subprocess
import sys
import unittest

from tests.fixtures import make_good_project
from tests.helpers import REPO, TempRepo


def session(root, messages):
    env = {**os.environ, "SF_ROOT": str(root)}
    payload = "\n".join(json.dumps(m, ensure_ascii=False) for m in messages) + "\n"
    out = subprocess.run([sys.executable, str(REPO / "mcp" / "server.py")], input=payload, capture_output=True,
                         text=True, env=env, timeout=60).stdout
    return [json.loads(l) for l in out.splitlines() if l.strip()]


class McpServerTest(unittest.TestCase):
    def test_handshake_list_and_call(self):
        with TempRepo() as root:
            make_good_project(root)
            replies = session(root, [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "sf_validate", "arguments": {"final": True}}},
                {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "sf_claims_trace", "arguments": {"id": "C2"}}},
                {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "sf_evidence_show", "arguments": {}}},
                {"jsonrpc": "2.0", "id": 6, "method": "nope"},
            ])
            by_id = {r["id"]: r for r in replies}
            self.assertEqual(len(replies), 6)                                  # уведомление без ответа
            self.assertEqual(by_id[1]["result"]["serverInfo"]["name"], "strategist")
            names = {t["name"] for t in by_id[2]["result"]["tools"]}
            self.assertIn("sf_revisit", names)
            self.assertFalse(by_id[3]["result"]["isError"])
            self.assertIn("ошибок 0", by_id[3]["result"]["content"][0]["text"])
            self.assertIn("удержание падает", by_id[4]["result"]["content"][0]["text"])
            self.assertTrue(by_id[5]["result"]["isError"])                     # не хватает ids
            self.assertEqual(by_id[6]["error"]["code"], -32601)

    def test_failing_validation_is_reported_as_error(self):
        with TempRepo() as root:
            p = make_good_project(root)
            (p / "outputs" / "research.md").write_text("# Исследование\n\nРост 35%.\n", encoding="utf-8")
            replies = session(root, [{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                      "params": {"name": "sf_validate", "arguments": {}}}])
            self.assertTrue(replies[0]["result"]["isError"])
            self.assertIn("число без метки", replies[0]["result"]["content"][0]["text"])


    def test_new_tools_report_price_and_watch_are_exposed(self):
        with TempRepo() as root:
            p = make_good_project(root)
            (p / "gg.csv").write_text("price,shown,bought\n99,40,6\n149,40,5\n", encoding="utf-8")
            replies = session(root, [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "sf_report", "arguments": {}}},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "sf_price", "arguments": {"method": "gg", "file": "gg.csv"}}},
            ])
            by_id = {r["id"]: r for r in replies}
            names = {t["name"] for t in by_id[1]["result"]["tools"]}
            self.assertTrue({"sf_report", "sf_price", "sf_watch", "sf_focus"} <= names)
            self.assertFalse(by_id[2]["result"]["isError"])
            self.assertTrue((p / "outputs" / "report.html").exists())
            self.assertIn("Выручка на 100 показов", by_id[3]["result"]["content"][0]["text"])
            watch_tool = next(t for t in by_id[1]["result"]["tools"] if t["name"] == "sf_watch")
            self.assertIn("ids", watch_tool["inputSchema"]["properties"])   # сам сторож проверен без сети в test_layer9


if __name__ == "__main__":
    unittest.main()
