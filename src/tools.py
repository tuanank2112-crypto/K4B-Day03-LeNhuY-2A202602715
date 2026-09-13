"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND - CYBER GAMING ASSISTANT
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer cho Trợ lý Đặt máy Quán Net & Cyber Game.
Hỗ trợ đặt 1 hoặc nhiều máy đồng thời (Multi-seat booking) và hủy/đổi máy linh hoạt.
"""

import json
from typing import Dict, Any, List, Union

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Tra cứu máy trống tại Cyber Game
    {
        "name": "check_available_pcs",
        "description": "Tra cứu danh sách các máy tính chơi game còn trống trong Cyber Game theo từng khu vực (VIP, STANDARD, PRO_GAMING, STREAM, hoặc ALL). Trả về cấu hình chi tiết (CPU, GPU, Màn hình Hz) và giá/giờ chơi.",
        "parameters": {
            "type": "object",
            "properties": {
                "zone": {
                    "type": "string",
                    "description": "Khu vực máy cần tra cứu: 'VIP', 'STANDARD', 'PRO_GAMING', 'STREAM', hoặc 'ALL' (mặc định: 'ALL')",
                    "enum": ["VIP", "STANDARD", "PRO_GAMING", "STREAM", "ALL"]
                }
            },
            "required": []
        }
    },
    
    # Tool 2: Đặt và khóa giữ 1 hoặc nhiều máy chơi net cho hội viên
    {
        "name": "book_gaming_pc",
        "description": "Đặt giữ máy chơi game tại Cyber Game cho tài khoản hội viên. Hỗ trợ đặt 1 máy đơn lẻ hoặc nhiều máy cùng lúc (ví dụ: 'VIP-01, VIP-02' khi đi theo nhóm/team).",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Mã tài khoản hội viên của khách (ví dụ: 'NET2026', 'VIP_NHUY26')"
                },
                "pc_id": {
                    "type": "string",
                    "description": "Mã định danh của máy muốn đặt, có thể là 1 máy (ví dụ: 'VIP-08') hoặc danh sách nhiều máy cách nhau bởi dấu phẩy (ví dụ: 'VIP-01, VIP-02')"
                },
                "duration_hours": {
                    "type": "integer",
                    "description": "Số giờ chơi muốn đặt trước (ví dụ: 2, 3, 5)"
                }
            },
            "required": ["customer_id", "pc_id", "duration_hours"]
        }
    },

    # Tool 3: Hủy đặt hoặc đổi máy đã giữ
    {
        "name": "cancel_or_release_pc",
        "description": "Hủy đặt hoặc giải phóng máy đã giữ trước đó để đổi sang máy khác hoặc hoàn tiền cọc thời gian chơi.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Mã tài khoản hội viên yêu cầu hủy đặt máy"
                },
                "pc_id": {
                    "type": "string",
                    "description": "Mã máy cần hủy/đổi (ví dụ: 'VIP-08')"
                }
            },
            "required": ["customer_id", "pc_id"]
        }
    },

    # Tool 4: Tra cứu thực đơn đồ ăn đêm & nước uống Canteen
    {
        "name": "get_canteen_menu",
        "description": "Tra cứu thực đơn đồ ăn, nước uống, mì tôm trứng, cơm chiên, nước ngọt tại Canteen Cyber Gaming Hub. Trả về chi tiết giá tiền và tình trạng món ăn.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Phân loại món ăn: 'FOOD' (Đồ ăn chính), 'DRINK' (Nước uống/Cà phê), 'SNACK' (Ăn vặt), hoặc 'ALL'",
                    "enum": ["FOOD", "DRINK", "SNACK", "ALL"]
                }
            },
            "required": []
        }
    },

    # Tool 5: Đặt đồ ăn / nước uống phục vụ tận máy
    {
        "name": "order_canteen_item",
        "description": "Đặt đồ ăn hoặc nước uống từ Canteen Cyber Gaming phục vụ tận máy cho hội viên.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Mã tài khoản hội viên đặt món (ví dụ: 'NET2026')"
                },
                "item_name": {
                    "type": "string",
                    "description": "Tên món ăn/nước uống muốn đặt (ví dụ: 'Mì tôm trứng xúc xích', 'Sting dâu')"
                },
                "pc_id": {
                    "type": "string",
                    "description": "Mã máy hội viên đang ngồi hoặc vừa đặt (ví dụ: 'VIP-08')"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Số lượng suất muốn đặt (mặc định: 1)"
                }
            },
            "required": ["customer_id", "item_name"]
        }
    }
]

# ==============================================================================
# 2. CƠ SỞ DỮ LIỆU MẪU PHÒNG MÁY & HỘI VIÊN
# ==============================================================================

MOCK_PC_DATABASE = {
    # Khu VIP (VIP-01 -> VIP-08)
    "VIP-01": {"zone": "VIP", "specs": "Intel Core i7-14700K | RTX 4070 Ti Super | Màn 2K 240Hz Fast-IPS", "status": "OCCUPIED", "price_per_hour": 18000},
    "VIP-02": {"zone": "VIP", "specs": "Intel Core i7-14700K | RTX 4070 Ti Super | Màn 2K 240Hz Fast-IPS", "status": "AVAILABLE", "price_per_hour": 18000},
    "VIP-03": {"zone": "VIP", "specs": "Intel Core i7-14700K | RTX 4070 Ti Super | Màn 2K 240Hz Fast-IPS", "status": "BOOKED", "booked_by": "NET1001", "price_per_hour": 18000},
    "VIP-04": {"zone": "VIP", "specs": "Intel Core i7-14700K | RTX 4070 Ti Super | Màn 2K 240Hz Fast-IPS", "status": "OCCUPIED", "price_per_hour": 18000},
    "VIP-05": {"zone": "VIP", "specs": "Intel Core i7-14700K | RTX 4070 Ti Super | Màn 2K 240Hz Fast-IPS", "status": "AVAILABLE", "price_per_hour": 18000},
    "VIP-06": {"zone": "VIP", "specs": "Intel Core i7-14700K | RTX 4070 Ti Super | Màn 2K 240Hz Fast-IPS", "status": "MAINTENANCE", "price_per_hour": 18000},
    "VIP-07": {"zone": "VIP", "specs": "Intel Core i7-14700K | RTX 4070 Ti Super | Màn 2K 240Hz Fast-IPS", "status": "OCCUPIED", "price_per_hour": 18000},
    "VIP-08": {"zone": "VIP", "specs": "Intel Core i7-14700K | RTX 4070 Ti Super | Màn 2K 240Hz Fast-IPS", "status": "AVAILABLE", "price_per_hour": 18000},

    # Khu PRO GAMING (PRO-01 -> PRO-06)
    "PRO-01": {"zone": "PRO_GAMING", "specs": "Intel Core i9-14900KS | RTX 4090 24GB | Màn BenQ ZOWIE XL2566K 360Hz | Ghế gaming Herman Miller", "status": "AVAILABLE", "price_per_hour": 25000},
    "PRO-02": {"zone": "PRO_GAMING", "specs": "Intel Core i9-14900KS | RTX 4090 24GB | Màn BenQ ZOWIE XL2566K 360Hz | Ghế gaming Herman Miller", "status": "OCCUPIED", "price_per_hour": 25000},
    "PRO-03": {"zone": "PRO_GAMING", "specs": "Intel Core i9-14900KS | RTX 4090 24GB | Màn BenQ ZOWIE XL2566K 360Hz | Ghế gaming Herman Miller", "status": "OCCUPIED", "price_per_hour": 25000},
    "PRO-04": {"zone": "PRO_GAMING", "specs": "Intel Core i9-14900KS | RTX 4090 24GB | Màn BenQ ZOWIE XL2566K 360Hz | Ghế gaming Herman Miller", "status": "AVAILABLE", "price_per_hour": 25000},
    "PRO-05": {"zone": "PRO_GAMING", "specs": "Intel Core i9-14900KS | RTX 4090 24GB | Màn BenQ ZOWIE XL2566K 360Hz | Ghế gaming Herman Miller", "status": "BOOKED", "booked_by": "NET1001", "price_per_hour": 25000},
    "PRO-06": {"zone": "PRO_GAMING", "specs": "Intel Core i9-14900KS | RTX 4090 24GB | Màn BenQ ZOWIE XL2566K 360Hz | Ghế gaming Herman Miller", "status": "OCCUPIED", "price_per_hour": 25000},

    # Khu STANDARD (STD-01 -> STD-16)
    "STD-01": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "OCCUPIED", "price_per_hour": 10000},
    "STD-02": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "AVAILABLE", "price_per_hour": 10000},
    "STD-03": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "AVAILABLE", "price_per_hour": 10000},
    "STD-04": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "OCCUPIED", "price_per_hour": 10000},
    "STD-05": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "AVAILABLE", "price_per_hour": 10000},
    "STD-06": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "MAINTENANCE", "price_per_hour": 10000},
    "STD-07": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "OCCUPIED", "price_per_hour": 10000},
    "STD-08": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "AVAILABLE", "price_per_hour": 10000},
    "STD-09": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "OCCUPIED", "price_per_hour": 10000},
    "STD-10": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "AVAILABLE", "price_per_hour": 10000},
    "STD-11": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "OCCUPIED", "price_per_hour": 10000},
    "STD-12": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "AVAILABLE", "price_per_hour": 10000},
    "STD-13": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "BOOKED", "booked_by": "NET1001", "price_per_hour": 10000},
    "STD-14": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "OCCUPIED", "price_per_hour": 10000},
    "STD-15": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "AVAILABLE", "price_per_hour": 10000},
    "STD-16": {"zone": "STANDARD", "specs": "Intel Core i5-13400F | RTX 3060 12GB | Màn FHD 165Hz IPS", "status": "OCCUPIED", "price_per_hour": 10000},

    # Khu STREAM (STREAM-01, STREAM-02)
    "STREAM-01": {"zone": "STREAM", "specs": "Dual PC Setup (i9-14900K + RTX 4080) | Mic Shure SM7B | Cam Sony A6400 | Phòng cách âm riêng", "status": "AVAILABLE", "price_per_hour": 45000},
    "STREAM-02": {"zone": "STREAM", "specs": "Dual PC Setup (i9-14900K + RTX 4080) | Mic Shure SM7B | Cam Sony A6400 | Phòng cách âm riêng", "status": "OCCUPIED", "price_per_hour": 45000}
}

MOCK_MEMBER_DATABASE = {
    "NET2026": {
        "name": "Hội viên NET2026",
        "tier": "Diamond VIP",
        "balance": 250000,
        "favorite_zone": "VIP"
    },
    "NET1001": {
        "name": "Trần Anh Quân",
        "tier": "Gold Member",
        "balance": 80000,
        "favorite_zone": "PRO_GAMING"
    }
}

MOCK_CANTEEN_DATABASE = {
    "Mì tôm trứng xúc xích": {"category": "FOOD", "price": 25000, "status": "AVAILABLE", "specs": "Mì Kokomi/Hảo Hảo + 1 trứng ốp la + 1 xúc xích chiên nóng"},
    "Mì xào bò rau cải": {"category": "FOOD", "price": 35000, "status": "AVAILABLE", "specs": "Mì xào thịt bò Mỹ phi tỏi tơ + rau cải ngọt"},
    "Cơm chiên dưa bò": {"category": "FOOD", "price": 40000, "status": "AVAILABLE", "specs": "Cơm rang giòn rụm với dưa chua & thịt bò xào sần sật"},
    "Bánh mì pate trứng": {"category": "FOOD", "price": 20000, "status": "AVAILABLE", "specs": "Bánh mì nướng giòn kẹp pate Hải Phòng & trứng chiên nóng"},
    "Sting dâu / vàng": {"category": "DRINK", "price": 15000, "status": "AVAILABLE", "specs": "Chai/Lon Sting ướp lạnh sâu"},
    "Cà phê muối": {"category": "DRINK", "price": 25000, "status": "AVAILABLE", "specs": "Cà phê phin đậm đà phủ kem muối béo ngậy"},
    "Trà đào cam sả": {"category": "DRINK", "price": 30000, "status": "AVAILABLE", "specs": "Trà đào mát lạnh kèm 3 miếng đào giòn tan"},
    "RedBull Thái": {"category": "DRINK", "price": 20000, "status": "AVAILABLE", "specs": "Bò húc Thái lon cao lạnh tỉnh táo nạp năng lượng"}
}


def execute_check_available_pcs(zone: str = "ALL") -> str:
    """Tra cứu máy chơi game còn trống theo khu vực"""
    zone_upper = (zone or "ALL").strip().upper()
    available_pcs = {}
    
    for pc_id, info in MOCK_PC_DATABASE.items():
        if info["status"] == "AVAILABLE":
            if zone_upper in ["ALL", ""] or info["zone"].upper() == zone_upper:
                available_pcs[pc_id] = info
                
    if available_pcs:
        return json.dumps({
            "status": "SUCCESS",
            "zone_filter": zone_upper,
            "total_available": len(available_pcs),
            "pcs": available_pcs,
            "message": f"Tìm thấy {len(available_pcs)} máy trống phù hợp ở khu vực {zone_upper}."
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "NOT_FOUND",
            "zone_filter": zone_upper,
            "total_available": 0,
            "message": f"Hiện tại không còn máy trống nào ở khu vực '{zone_upper}'. Quý khách vui lòng chọn khu vực khác."
        }, ensure_ascii=False)


def execute_book_gaming_pc(customer_id: str, pc_id: Union[str, List[str]], duration_hours: int = 2) -> str:
    """
    Thực thi đặt giữ máy chơi net cho hội viên.
    Hỗ trợ cả 1 máy hoặc nhiều máy (ví dụ: 'VIP-01, VIP-02' hoặc list).
    """
    # Xử lý danh sách các mã máy
    if isinstance(pc_id, list):
        pc_keys = [str(p).strip().upper() for p in pc_id if str(p).strip()]
    else:
        pc_keys = [p.strip().upper() for p in str(pc_id).replace(";", ",").split(",") if p.strip()]

    if not pc_keys:
        return json.dumps({
            "status": "ERROR",
            "message": "Vui lòng chỉ định ít nhất 1 mã máy để đặt chỗ!"
        }, ensure_ascii=False)

    member = MOCK_MEMBER_DATABASE.get(customer_id.strip().upper(), {
        "name": f"Hội viên {customer_id}",
        "tier": "Standard"
    })

    # Trường hợp đặt 1 máy đơn lẻ (tương thích 100% test suite cũ)
    if len(pc_keys) == 1:
        pc_key = pc_keys[0]
        if pc_key not in MOCK_PC_DATABASE:
            return json.dumps({
                "status": "NOT_FOUND",
                "error_code": "PC_DOES_NOT_EXIST",
                "message": f"Lỗi: Không tồn tại máy có mã '{pc_key}' trong hệ thống Cyber Game!"
            }, ensure_ascii=False)
            
        pc_info = MOCK_PC_DATABASE[pc_key]
        if pc_info["status"] != "AVAILABLE":
            return json.dumps({
                "status": "OCCUPIED",
                "error_code": "PC_ALREADY_OCCUPIED",
                "message": f"Máy '{pc_key}' hiện đang có người chơi hoặc đã được đặt trước. Vui lòng chọn máy khác!"
            }, ensure_ascii=False)
            
        total_cost = int(pc_info["price_per_hour"]) * int(duration_hours)
        booking_code = f"CYBER-{pc_key}-{customer_id[-4:]}"
        
        # Cập nhật trạng thái máy
        pc_info["status"] = "BOOKED"
        pc_info["booked_by"] = customer_id.strip().upper()
        pc_info["booking_id"] = booking_code
        pc_info["duration_hours"] = duration_hours
        
        return json.dumps({
            "status": "SUCCESS",
            "booking_id": booking_code,
            "customer_id": customer_id,
            "customer_name": member["name"],
            "pc_id": pc_key,
            "zone": pc_info["zone"],
            "duration_hours": duration_hours,
            "price_per_hour": pc_info["price_per_hour"],
            "total_cost": total_cost,
            "specs": pc_info["specs"],
            "message": f"Đặt máy thành công! Mã đặt: {booking_code}. Máy {pc_key} ({pc_info['zone']}) đã được giữ cho {member['name']} trong {duration_hours} giờ. Tổng phí tạm tính: {total_cost:,} VNĐ."
        }, ensure_ascii=False)

    # Trường hợp đặt NHIỀU MÁY cùng lúc (Multi-seat booking)
    success_pcs = []
    failed_pcs = []
    total_cost = 0

    for pk in pc_keys:
        if pk not in MOCK_PC_DATABASE:
            failed_pcs.append(f"{pk} (không tồn tại)")
        elif MOCK_PC_DATABASE[pk]["status"] != "AVAILABLE":
            failed_pcs.append(f"{pk} (đang bận/đã đặt)")
        else:
            info = MOCK_PC_DATABASE[pk]
            cost = int(info["price_per_hour"]) * int(duration_hours)
            total_cost += cost
            info["status"] = "BOOKED"
            info["booked_by"] = customer_id.strip().upper()
            b_code = f"CYBER-{pk}-{customer_id[-4:]}"
            info["booking_id"] = b_code
            info["duration_hours"] = duration_hours
            success_pcs.append(pk)

    if not success_pcs:
        return json.dumps({
            "status": "OCCUPIED",
            "message": f"Không thể đặt các máy đã chọn do: {', '.join(failed_pcs)}. Vui lòng chọn các máy khác còn trống!"
        }, ensure_ascii=False)

    msg = (
        f"Đặt thành công {len(success_pcs)} máy: {', '.join(success_pcs)} cho {member['name']} trong {duration_hours} giờ. "
        f"Tổng phí tạm tính: {total_cost:,} VNĐ."
    )
    if failed_pcs:
        msg += f" (Lưu ý: Không thể giữ các máy: {', '.join(failed_pcs)})"

    return json.dumps({
        "status": "SUCCESS",
        "booking_id": f"MULTI-CYBER-{customer_id[-4:]}",
        "customer_id": customer_id,
        "customer_name": member["name"],
        "booked_pcs": success_pcs,
        "failed_pcs": failed_pcs,
        "duration_hours": duration_hours,
        "total_cost": total_cost,
        "message": msg
    }, ensure_ascii=False)


def execute_cancel_or_release_pc(customer_id: str, pc_id: str, held_minutes: int = 30) -> str:
    """
    Hủy đặt máy hoặc đổi máy đã giữ.
    Tính toán chi phí giữ máy thực tế (khấu trừ) và số tiền hoàn lại.
    Hướng dẫn khách hàng đến quầy lễ tân gặp nhân viên để nhận tiền hoàn hoặc cấn trừ tiền cọc.
    """
    pc_key = pc_id.strip().upper()
    if pc_key not in MOCK_PC_DATABASE:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy máy '{pc_id}' trong hệ thống!"
        }, ensure_ascii=False)
        
    pc_info = MOCK_PC_DATABASE[pc_key]
    if pc_info["status"] != "BOOKED":
        return json.dumps({
            "status": "ERROR",
            "message": f"Máy '{pc_key}' hiện không ở trạng thái Đang đặt (BOOKED)."
        }, ensure_ascii=False)

    # 🛡️ CƠ CHẾ BẢO VỆ PHÂN QUYỀN: Không cho phép hủy máy được đặt bởi hội viên khác
    booked_by = pc_info.get("booked_by")
    if booked_by and customer_id and booked_by != customer_id.strip().upper():
        return json.dumps({
            "status": "FORBIDDEN",
            "error_code": "UNAUTHORIZED_CANCELLATION",
            "message": f"Lỗi bảo mật: Máy '{pc_key}' đang được giữ bởi hội viên '{booked_by}'. Tài khoản của bạn ({customer_id}) không có quyền hủy máy này!"
        }, ensure_ascii=False)
        
    price_per_hour = pc_info.get("price_per_hour", 18000)
    duration_hours = pc_info.get("duration_hours", 2)
    initial_cost = price_per_hour * duration_hours
    
    # Khấu trừ tiền thời gian đã giữ máy (tính theo số phút / 60)
    deducted_fee = int((price_per_hour / 60) * held_minutes)
    refund_amount = max(0, initial_cost - deducted_fee)
    refund_code = f"REFUND-{pc_key}-{customer_id[-4:]}"
    
    # Giải phóng máy
    pc_info["status"] = "AVAILABLE"
    pc_info.pop("booked_by", None)
    pc_info.pop("booking_id", None)
    pc_info.pop("duration_hours", None)
    
    return json.dumps({
        "status": "SUCCESS",
        "pc_id": pc_key,
        "customer_id": customer_id,
        "refund_code": refund_code,
        "duration_hours": duration_hours,
        "held_minutes": held_minutes,
        "initial_cost": initial_cost,
        "deducted_fee": deducted_fee,
        "refund_amount": refund_amount,
        "counter_notice": "Quý khách vui lòng đến quầy lễ tân gặp nhân viên thu ngân để nhận lại tiền hoàn hoặc cấn trừ tiền sang máy mới!",
        "message": (
            f"Hủy đặt máy {pc_key} thành công! Thời gian máy đã giữ chỗ: {held_minutes} phút. "
            f"Phí giữ máy đã trừ: {deducted_fee:,} VNĐ. Số tiền hoàn lại dự kiến: {refund_amount:,} VNĐ (Mã phiếu: {refund_code}). "
            f"⚠️ LƯU Ý QUAN TRỌNG: Quý khách vui lòng đến quầy lễ tân gặp nhân viên thu ngân để nhận lại tiền hoàn hoặc cấn trừ sang máy mới nhé!"
        )
    }, ensure_ascii=False)


def execute_get_canteen_menu(category: str = "ALL") -> str:
    """Tra cứu thực đơn đồ ăn & nước uống từ CSDL Canteen"""
    cat_upper = (category or "ALL").strip().upper()
    filtered_menu = {}
    
    for item_name, info in MOCK_CANTEEN_DATABASE.items():
        if cat_upper in ["ALL", ""] or info["category"].upper() == cat_upper:
            filtered_menu[item_name] = info
            
    return json.dumps({
        "status": "SUCCESS",
        "category_filter": cat_upper,
        "total_items": len(filtered_menu),
        "menu": filtered_menu,
        "message": f"Tra cứu CSDL Canteen thành công! Tìm thấy {len(filtered_menu)} món thuộc nhóm '{cat_upper}'."
    }, ensure_ascii=False)


def execute_order_canteen_item(customer_id: str, item_name: str, pc_id: str = "TẠI QUẦY", quantity: int = 1) -> str:
    """Đặt đồ ăn/nước uống phục vụ tận máy cho hội viên"""
    matched_item = None
    item_clean = (item_name or "").strip().lower()
    
    for key, info in MOCK_CANTEEN_DATABASE.items():
        if item_clean in key.lower() or key.lower() in item_clean or "mì" in item_clean and "mì" in key.lower():
            matched_item = (key, info)
            break
            
    if not matched_item:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy món '{item_name}' trong CSDL Canteen! Vui lòng gọi tool get_canteen_menu để xem thực đơn."
        }, ensure_ascii=False)
        
    full_name, item_info = matched_item
    total_cost = item_info["price"] * quantity
    order_code = f"ORDER-{customer_id[-4:]}-{quantity}"
    
    return json.dumps({
        "status": "SUCCESS",
        "order_id": order_code,
        "customer_id": customer_id,
        "pc_id": pc_id,
        "item_name": full_name,
        "quantity": quantity,
        "unit_price": item_info["price"],
        "total_cost": total_cost,
        "message": f"Đặt món Canteen thành công! Mã đơn: {order_code}. Đơn hàng {quantity}x {full_name} ({total_cost:,} VNĐ) sẽ được nhân viên Canteen mang tới máy {pc_id} cho hội viên {customer_id}."
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "check_available_pcs": execute_check_available_pcs,
    "book_gaming_pc": execute_book_gaming_pc,
    "cancel_or_release_pc": execute_cancel_or_release_pc,
    "get_canteen_menu": execute_get_canteen_menu,
    "order_canteen_item": execute_order_canteen_item
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại trong hệ thống Cyber Game!"}, ensure_ascii=False)
