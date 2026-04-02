import argparse
import json
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from streamlit.web import bootstrap

from virtual_sales_agent import settings
from virtual_sales_agent.runtime import AgentRuntime


class ChatHandler(BaseHTTPRequestHandler):
    def _write_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/chat":
            self._write_json(404, {"error": "Not found"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        payload = json.loads(raw_body.decode("utf-8") or "{}")

        customer_id = payload.get("customer_id") or settings.CUSTOMER_ID or str(uuid.uuid4())
        thread_id = payload.get("thread_id") or settings.THREAD_ID or str(uuid.uuid4())
        runtime = self.server.runtime_cls.get_or_create(customer_id, thread_id)

        approval = payload.get("approval")
        if approval is not None:
            decision = approval.get("decision")
            if decision == "approve":
                result = runtime.approve()
                self._write_json(200, result)
                return
            if decision == "deny":
                reason = approval.get("reason", "No reason provided")
                result = runtime.deny(reason)
                self._write_json(200, result)
                return
            self._write_json(400, {"error": "approval.decision must be approve or deny"})
            return

        message = payload["message"]
        result = runtime.chat(message)
        self._write_json(200, result)

    def log_message(self, format: str, *args) -> None:
        return


class AppServer(ThreadingHTTPServer):
    def __init__(self, host: str, port: int, runtime_cls):
        super().__init__((host, port), ChatHandler)
        self.runtime_cls = runtime_cls


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Virtual Sales Agent")
    parser.add_argument("--mode", choices=["gui", "api", "chat"], default="gui")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--customer-id", default=None)
    parser.add_argument("--thread-id", default=None)
    parser.add_argument("--llm-model", default="unsloth/Qwen3-Next-Instruct")
    parser.add_argument("--llm-base-url", default="http://localhost:8001/v1")
    parser.add_argument("--llm-api-key", default="")
    parser.add_argument("--prompt", default=None)
    return parser.parse_args()


def run_streamlit() -> int:
    flag_options = {
        "server.address": settings.HOST,
        "server.port": settings.PORT,
    }
    bootstrap.run("streamlit_app.py", False, [], flag_options)
    return 0


def run_chat(prompt: str | None, customer_id: str | None, thread_id: str | None) -> int:
    if prompt is None:
        print("--prompt is required in chat mode")
        return 2

    runtime_customer_id = customer_id or str(uuid.uuid4())
    runtime_thread_id = thread_id or str(uuid.uuid4())
    runtime = AgentRuntime.get_or_create(runtime_customer_id, runtime_thread_id)

    response = runtime.chat(prompt)
    response_json = json.dumps(response, ensure_ascii=False)
    print(response_json)
    return 0


def run_api() -> int:
    server = AppServer(settings.HOST, settings.PORT, AgentRuntime)
    print(f"API server listening on http://{settings.HOST}:{settings.PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    return 0


def main() -> int:
    args = parse_args()
    settings.configure(args)

    if args.mode == "gui":
        return run_streamlit()

    if args.mode == "api":
        return run_api()

    if args.mode == "chat":
        return run_chat(args.prompt, args.customer_id, args.thread_id)

    print(f"Unsupported mode: {args.mode}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
