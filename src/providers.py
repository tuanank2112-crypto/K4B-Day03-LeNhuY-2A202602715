"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi là Trợ lý Cyber Gaming Hub. Quán mở cửa 24/7 với đầy đủ menu đồ ăn đêm (mì tôm trứng 25k, nước ngọt 15k) và các dàn máy VIP, Pro Gaming, Standard, Stream."

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        
        # Nếu đã có kết quả Observation từ các bước trước -> Trả lời hoàn tất
        if "[tool call" in prompt_lower or "[observation" in prompt_lower:
            return {
                "type": "text",
                "content": "Mình đã xử lý xong toàn bộ các yêu cầu của bạn qua hệ thống MCP Server! Đơn hàng và phòng máy đã được cập nhật thành công. Chúc bạn chơi game thật vui tại Cyber Gaming Hub! 🎮✨",
                "thought": "Đã nhận đủ kết quả Observation từ các công cụ MCP. Phản hồi xác nhận hoàn tất dịch vụ cho khách hàng."
            }

        # Trích xuất mã máy nếu có trong prompt
        pc_target = "VIP-08"
        for p in ["vip-01", "vip-02", "vip-03", "vip-04", "vip-05", "vip-06", "vip-07", "vip-08",
                  "vip01", "vip02", "vip03", "vip04", "vip05", "vip06", "vip07", "vip08",
                  "pro-01", "pro-02", "pro-03", "pro-04", "pro-05", "pro-06",
                  "pro01", "pro02", "pro03", "pro04", "pro05", "pro06",
                  "std-01", "std-02", "std-03", "std-04", "std-05"]:
            if p in prompt_lower:
                pc_target = p.upper().replace("VIP0", "VIP-0").replace("PRO0", "PRO-0").replace("STD0", "STD-0")
                if "-" not in pc_target and len(pc_target) >= 4:
                    pc_target = f"{pc_target[:3]}-{pc_target[3:]}"
                break

        # 0. COMBO ĐẶC BIỆT: Gọi ĐỒ ĂN + NƯỚC UỐNG (Ví dụ: 1 bát mì tôm + 1 Sting dâu) -> GỌI 2 TOOLS
        has_food = any(w in prompt_lower for w in ["mì", "mỳ", "cơm", "bánh mì"])
        has_drink = any(w in prompt_lower for w in ["sting", "nước", "bò húc", "cà phê", "trà"])
        if has_food and has_drink and not any(w in prompt_lower for w in ["thực đơn", "menu", "giá"]):
            return {
                "type": "tool_calls",
                "tool_calls": [
                    {
                        "tool_name": "order_canteen_item",
                        "arguments": {"customer_id": "NET2026", "item_name": "Mì tôm trứng xúc xích", "pc_id": pc_target, "quantity": 1}
                    },
                    {
                        "tool_name": "order_canteen_item",
                        "arguments": {"customer_id": "NET2026", "item_name": "Sting dâu", "pc_id": pc_target, "quantity": 1}
                    }
                ],
                "thought": f"Khách yêu cầu Combo ẩm thực Canteen (1 Mì tôm trứng xúc xích và 1 Sting dâu giao máy {pc_target}). Kích hoạt đồng thời 2 công cụ order_canteen_item qua MCP."
            }

        # 0.5. COMBO ĐẶC BIỆT: ĐẶT MÁY + GỌI ĐỒ ĂN (Ví dụ: Đặt máy VIP-02 và cho 1 bát mì) -> GỌI 2 TOOLS
        has_booking = any(w in prompt_lower for w in ["đặt máy", "giữ máy", "book máy", "chọn máy"])
        if has_booking and (has_food or has_drink):
            return {
                "type": "tool_calls",
                "tool_calls": [
                    {
                        "tool_name": "book_gaming_pc",
                        "arguments": {"customer_id": "NET2026", "pc_id": pc_target, "duration_hours": 2}
                    },
                    {
                        "tool_name": "order_canteen_item",
                        "arguments": {"customer_id": "NET2026", "item_name": "Mì tôm trứng xúc xích", "pc_id": pc_target, "quantity": 1}
                    }
                ],
                "thought": f"Khách yêu cầu Combo 2 tác vụ: Đặt máy {pc_target} và gọi Canteen phục vụ tận máy. Kích hoạt đồng thời 2 công cụ book_gaming_pc và order_canteen_item qua MCP."
            }

        # 1. Đặt lẻ đồ ăn / Nước uống Canteen (1 tool)
        if (has_food or has_drink) and not any(w in prompt_lower for w in ["thực đơn", "menu", "giá"]):
            item = "Mì tôm trứng xúc xích"
            if has_drink: item = "Sting dâu"
            elif "cơm" in prompt_lower: item = "Cơm rang dưa bò"
            elif "bánh mì" in prompt_lower: item = "Bánh mì pate trứng"
            return {
                "type": "tool_call",
                "tool_name": "order_canteen_item",
                "arguments": {"customer_id": "NET2026", "item_name": item, "pc_id": pc_target, "quantity": 1},
                "thought": f"Khách yêu cầu gọi món '{item}'. Kích hoạt tool order_canteen_item phục vụ mang ra máy {pc_target} cho hội viên NET2026."
            }
            
        # 2. Xem menu thực đơn Canteen
        elif any(w in prompt_lower for w in ["menu", "thực đơn", "món ăn", "đồ ăn", "nước gì", "bảng giá đồ ăn"]):
            return {
                "type": "tool_call",
                "tool_name": "get_canteen_menu",
                "arguments": {"category": "ALL"},
                "thought": "Khách hỏi thông tin menu Canteen. Kích hoạt tool get_canteen_menu để tra cứu danh sách món ăn & nước uống."
            }

        # 3. Đặt giữ máy chơi game lẻ (1 tool)
        elif any(w in prompt_lower for w in ["đặt máy", "giữ máy", "book", "chọn máy", "đặt chỗ", "khóa máy"]):
            return {
                "type": "tool_call",
                "tool_name": "book_gaming_pc",
                "arguments": {"customer_id": "NET2026", "pc_id": pc_target, "duration_hours": 2},
                "thought": f"Khách yêu cầu đặt giữ máy {pc_target}. Kích hoạt tool book_gaming_pc khóa máy 2 giờ cho hội viên NET2026."
            }

        # 4. Hủy đặt hoặc đổi máy
        elif any(w in prompt_lower for w in ["hủy", "đổi máy", "trả máy", "hoàn tiền"]):
            return {
                "type": "tool_call",
                "tool_name": "cancel_or_release_pc",
                "arguments": {"customer_id": "NET2026", "pc_id": pc_target},
                "thought": f"Khách muốn hủy hoặc đổi máy {pc_target} đã đặt. Kích hoạt tool cancel_or_release_pc và tính tiền cấn trừ/hoàn lại tại quầy lễ tân."
            }

        # 5. Tra cứu máy trống
        elif any(w in prompt_lower for w in ["máy trống", "phòng máy", "còn máy", "khu", "vip", "pro", "standard", "stream", "cấu hình"]):
            zone = "ALL"
            if "vip" in prompt_lower: zone = "VIP"
            elif "pro" in prompt_lower: zone = "PRO_GAMING"
            elif "standard" in prompt_lower or "thường" in prompt_lower: zone = "STANDARD"
            elif "stream" in prompt_lower: zone = "STREAM"
            return {
                "type": "tool_call",
                "tool_name": "check_available_pcs",
                "arguments": {"zone": zone},
                "thought": f"Khách cần tra cứu danh sách máy đang trống khu vực {zone}. Kích hoạt tool check_available_pcs."
            }
            
        else:
            return {
                "type": "text",
                "content": "Chào bạn! Mình là Trợ lý AI Cyber Gaming Hub. Bạn có thể tra cứu máy trống, đặt giữ nhiều máy cùng lúc, hoặc gọi mì tôm trứng / nước ngọt phục vụ tận máy nhé!",
                "thought": "Chào hỏi tổng quan dịch vụ phòng máy, không cần gọi tool."
            }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                parsed_calls = []
                for call in response.function_calls:
                    args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                    parsed_calls.append({
                        "tool_name": call.name,
                        "arguments": args
                    })
                tool_names_str = ", ".join(f"'{c['tool_name']}'" for c in parsed_calls)
                return {
                    "type": "tool_calls" if len(parsed_calls) > 1 else "tool_call",
                    "tool_name": parsed_calls[0]["tool_name"],
                    "arguments": parsed_calls[0]["arguments"],
                    "tool_calls": parsed_calls,
                    "thought": f"Gemini quyết định gọi {len(parsed_calls)} công cụ qua MCP ({tool_names_str}) với đầy đủ tham số."
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                parsed_calls = []
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except Exception:
                        args = {}
                    parsed_calls.append({
                        "tool_name": tc.function.name,
                        "arguments": args
                    })
                tool_names_str = ", ".join(f"'{c['tool_name']}'" for c in parsed_calls)
                return {
                    "type": "tool_calls" if len(parsed_calls) > 1 else "tool_call",
                    "tool_name": parsed_calls[0]["tool_name"],
                    "arguments": parsed_calls[0]["arguments"],
                    "tool_calls": parsed_calls,
                    "thought": f"OpenAI quyết định gọi {len(parsed_calls)} công cụ qua MCP ({tool_names_str}) với đầy đủ tham số."
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
