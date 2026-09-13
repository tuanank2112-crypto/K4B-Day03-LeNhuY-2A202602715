"""
🌐 WEB SERVER & API BRIDGE - CYBER GAMING & NITRO AI UI
Cung cấp Web Server và REST API kết nối giao diện Cyber Game với MCP Server & ReAct Agent.
"""

import json
import os
import sys
import functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_server import MCPAcademicServer
from tools import (
    MOCK_PC_DATABASE, 
    MOCK_MEMBER_DATABASE, 
    execute_book_gaming_pc,
    execute_cancel_or_release_pc
)
from providers import get_llm_provider
from app import run_react_agent

PORT = 8080
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")

mcp_server = MCPAcademicServer()
provider = get_llm_provider()

class CyberWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/pcs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # Tính toán thống kê
            stats = {"TOTAL": len(MOCK_PC_DATABASE), "AVAILABLE": 0, "OCCUPIED": 0, "BOOKED": 0, "MAINTENANCE": 0}
            for info in MOCK_PC_DATABASE.values():
                st = info.get("status", "AVAILABLE")
                if st in stats:
                    stats[st] += 1
                else:
                    stats[st] = 1

            data = {
                "status": "SUCCESS",
                "center_name": "NITRO CYBER GAMING HUB",
                "stats": stats,
                "pcs": MOCK_PC_DATABASE
            }
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            return
            
        elif parsed.path == "/api/traces":
            trace_path = os.path.join(BASE_DIR, "docs", "trace_waterfall.json")
            traces = []
            if os.path.exists(trace_path):
                try:
                    with open(trace_path, "r", encoding="utf-8") as f:
                        traces = json.load(f)
                except Exception:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(traces, ensure_ascii=False).encode("utf-8"))
            return
            
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        try:
            req_data = json.loads(body) if body else {}
        except Exception:
            req_data = {}

        if parsed.path == "/api/book":
            customer_id = req_data.get("customer_id", "NET2026")
            # Hỗ trợ cả single pc_id hoặc mảng pc_ids
            pc_ids = req_data.get("pc_ids") or req_data.get("pc_id") or ""
            duration_hours = int(req_data.get("duration_hours", 2))
            
            result_str = execute_book_gaming_pc(customer_id=customer_id, pc_id=pc_ids, duration_hours=duration_hours)
            result_json = json.loads(result_str)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result_json, ensure_ascii=False).encode("utf-8"))
            return

        elif parsed.path == "/api/cancel":
            customer_id = req_data.get("customer_id", "NET2026")
            pc_id = req_data.get("pc_id", "")
            
            result_str = execute_cancel_or_release_pc(customer_id=customer_id, pc_id=pc_id)
            result_json = json.loads(result_str)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result_json, ensure_ascii=False).encode("utf-8"))
            return
            
        elif parsed.path == "/api/chat":
            message = req_data.get("message", "").strip()
            if not message:
                self.send_response(400)
                self.end_headers()
                return
                
            logs = run_react_agent(message, provider, mcp_server)
            final_answer = ""
            for item in reversed(logs):
                if item.get("action_type") == "FINAL_ANSWER":
                    final_answer = item.get("output", "")
                    break
            if not final_answer and logs:
                final_answer = "Đã thực hiện xong yêu cầu từ Agent."
                
            resp_payload = {
                "status": "SUCCESS",
                "message": message,
                "final_answer": final_answer,
                "trace_logs": logs
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(resp_payload, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def start_server(port=PORT):
    os.makedirs(WEB_DIR, exist_ok=True)
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, CyberWebHandler)
    print(f"🚀 [CYBER WEB SERVER] Đang chạy tại http://localhost:{port}", flush=True)
    print(f"📁 Phục vụ giao diện tại thư mục: {WEB_DIR}", flush=True)
    print(f"🌐 MCP Server: {mcp_server.server_name}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Đã tắt Cyber Web Server.", flush=True)
        httpd.server_close()

if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    start_server(p)
