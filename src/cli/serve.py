"""CLI: 启动给前端使用的轻量图谱 API 服务。"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from src.loader.neo4j_client import Neo4jClient
from src.query.graph_query import get_visual_graph


class _ApiHandler(BaseHTTPRequestHandler):
    server_version = "JDGraphBuilderAPI/0.1"
    sys_version = ""

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if parsed.path == "/api/graph":
            self._handle_graph(parsed.query)
            return
        self._send_json(404, {"error": "not found", "path": parsed.path})

    def _handle_graph(self, query_string: str) -> None:
        query = parse_qs(query_string)
        skill_limit = _parse_int(query.get("skill_limit", ["8"])[0], default=8, minimum=1, maximum=20)
        related_skill_limit = _parse_int(query.get("related_skill_limit", ["3"])[0], default=3, minimum=0, maximum=10)
        jobs_per_skill = _parse_int(query.get("jobs_per_skill", ["2"])[0], default=2, minimum=1, maximum=10)
        focus_skill = query.get("skill", [None])[0]

        try:
            with Neo4jClient() as client:
                payload = get_visual_graph(
                    client,
                    skill_limit=skill_limit,
                    related_skill_limit=related_skill_limit,
                    jobs_per_skill=jobs_per_skill,
                    focus_skill=focus_skill,
                )
        except Exception as exc:  # noqa: BLE001
            self._send_json(503, {"error": "neo4j_unavailable", "detail": str(exc)})
            return

        self._send_json(200, payload)

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def _parse_int(value: str, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def main(argv: list[str] | None = None) -> None:
    """启动 HTTP 服务。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(description="启动 JDGraphBuilder 图谱 API")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), _ApiHandler)
    print(f"JDGraphBuilder API running at http://{args.host}:{args.port}")
    print("GET /api/graph -> nodes / edges graph payload")
    print("GET /health -> health check")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
