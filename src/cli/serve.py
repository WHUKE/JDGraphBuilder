"""CLI: 启动给前端使用的轻量图谱 API 服务。"""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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
        if parsed.path == "/" or parsed.path.startswith("/front/"):
            self._serve_static(parsed.path)
            return
        self._send_json(404, {"error": "not found", "path": parsed.path})

    def _serve_static(self, request_path: str) -> None:
        if request_path == "/":
            request_path = "/front/woodle_ai_home.html"

        static_root = getattr(self.server, "frontend_root", None)
        if not static_root:
            self._send_json(404, {"error": "static_frontend_not_configured", "path": request_path})
            return

        relative_path = request_path.lstrip("/")
        if relative_path.startswith("front/"):
            relative_path = relative_path[len("front/"):]
        file_path = static_root.joinpath(relative_path).resolve()
        try:
            if not str(file_path).startswith(str(static_root.resolve())) or not file_path.exists() or not file_path.is_file():
                raise FileNotFoundError
        except (OSError, FileNotFoundError):
            self._send_json(404, {"error": "not found", "path": request_path})
            return

        content_type, _ = mimetypes.guess_type(file_path.name)
        if content_type:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        with file_path.open("rb") as handle:
            self.wfile.write(handle.read())

    def _handle_graph(self, query_string: str) -> None:
        query = parse_qs(query_string)
        related_skill_limit = _parse_int(query.get("related_skill_limit", ["3"])[0], default=3, minimum=0, maximum=10)
        jobs_per_skill = _parse_int(query.get("jobs_per_skill", ["2"])[0], default=2, minimum=1, maximum=10)
        focus_skill = query.get("skill", [None])[0]

        try:
            with Neo4jClient() as client:
                payload = get_visual_graph(
                    client,
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
    parser.add_argument(
        "--frontend-dir",
        default=None,
        help="静态前端目录，默认尝试 ../JDGraphMono/front",
    )
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), _ApiHandler)
    if args.frontend_dir:
        server.frontend_root = Path(args.frontend_dir).resolve()
    else:
        cwd = Path(__file__).resolve().parents[2]
        server.frontend_root = cwd.parent.joinpath("JDGraphMono", "front").resolve()

    print(f"JDGraphBuilder API running at http://{args.host}:{args.port}")
    print("GET /api/graph -> nodes / edges graph payload")
    print("GET /health -> health check")
    print("GET /front/* -> 静态前端页面 / assets")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
