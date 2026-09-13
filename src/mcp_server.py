"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE - CYBER GAMING
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa cho Cyber Game.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPAcademicServer:
    """
    MCP Server tuân thủ chuẩn giao thức Model Context Protocol cho Cyber Game Assistant
    """
    def __init__(self, server_name: str = "cyber-gaming-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        [TASK 2.1] HỌC VIÊN HOÀN THIỆN HÀM THỰC THI TOOL TRÊN MCP SERVER
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC 2.0
        """
        # 1. Gọi hàm trung chuyển dispatch_tool_call để lấy chuỗi JSON kết quả từ Tool Router
        raw_result = dispatch_tool_call(tool_name, arguments)
        
        # 2. Chuyển đổi chuỗi JSON kết quả thành Python Dictionary
        try:
            content = json.loads(raw_result)
        except Exception:
            content = {"raw_output": raw_result}
            
        # 3. Đóng gói phản hồi và trả về Dict theo đúng chuẩn giao thức MCP JSON-RPC 2.0
        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content
        }

# Alias để tương thích linh hoạt tên lớp
MCPCyberGameServer = MCPAcademicServer


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (cyber-gaming-mcp-server)")
    print("==========================================================")
    
    server = MCPAcademicServer()
    tools = server.list_tools()
    print(f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(tools)}")
    
    # Kiểm tra trạng thái các Tool Schemas
    for tool in tools:
        t_name = tool.get("name")
        props = tool.get("parameters", {}).get("properties", {})
        if props:
            print(f"✅ [TOOL SCHEMA]: Tool '{t_name}' đã được định nghĩa schema đầy đủ ({len(props)} tham số).")
        else:
            print(f"⏳ [TOOL SCHEMA]: Tool '{t_name}' chưa có properties.")

    # Kiểm tra trạng thái Task 2.1 (call_tool)
    test_result = server.call_tool("check_available_pcs", {"zone": "VIP"})
    if not test_result or not test_result.get("result"):
        print("⏳ [TASK 2.1]: Hàm call_tool() đang trả về rỗng. Học viên hãy hoàn thiện TASK 2.1!")
    else:
        print(f"✅ [TASK 2.1]: Test dispatch tool 'check_available_pcs' thành công:")
        print(f"   Phản hồi JSON-RPC: {json.dumps(test_result, ensure_ascii=False, indent=2)}")
