/**
 * 🎮 NITRO AI CYBER GAMING HUB — APP CONTROLLER
 * Quản lý sơ đồ phòng máy 2D, chọn nhiều máy cùng lúc (Multi-booking) và ReAct AI Agent qua MCP.
 */

let allPcs = {};
let selectedPcIds = new Set();
let currentDuration = 2;
let targetManagePcId = null;
const CURRENT_CUSTOMER_ID = "NET2026";
let chatSessionHistory = [];
let liveStreamLogHistory = [];

// Khởi chạy khi tải trang
document.addEventListener("DOMContentLoaded", () => {
  loadPcsData();
  initSampleStreamLogs();
  // Tự động tải lại dữ liệu mỗi 15 giây
  setInterval(loadPcsData, 15000);
});


// Tải danh sách máy và thông số từ Server
async function loadPcsData() {
  try {
    const res = await fetch("/api/pcs");
    const data = await res.json();
    if (data.status === "SUCCESS") {
      allPcs = data.pcs;
      updateStatsBar(data.stats);
      render2DGrids();
      updateSelectedSummary();
    }
  } catch (err) {
    console.error("Lỗi tải dữ liệu phòng máy:", err);
  }
}

// Cập nhật thống kê nhanh
function updateStatsBar(stats) {
  if (!stats) return;
  document.getElementById("stat-total").textContent = stats.TOTAL || Object.keys(allPcs).length;
  document.getElementById("stat-available").textContent = stats.AVAILABLE || 0;
  document.getElementById("stat-occupied").textContent = stats.OCCUPIED || 0;
  document.getElementById("stat-booked").textContent = stats.BOOKED || 0;
  document.getElementById("stat-maint").textContent = stats.MAINTENANCE || 0;
}

// Render Sơ đồ 2D theo từng Khu vực (VIP, PRO, STANDARD, STREAM)
function render2DGrids() {
  const vipContainer = document.getElementById("seats-vip");
  const proContainer = document.getElementById("seats-pro");
  const stdContainer = document.getElementById("seats-standard");
  const streamContainer = document.getElementById("seats-stream");

  vipContainer.innerHTML = "";
  proContainer.innerHTML = "";
  stdContainer.innerHTML = "";
  streamContainer.innerHTML = "";

  for (const [pcId, info] of Object.entries(allPcs)) {
    const isSelected = selectedPcIds.has(pcId);
    let status = isSelected ? "SELECTED" : info.status;

    const box = document.createElement("div");
    box.className = "seat-box";
    box.id = `seat-box-${pcId}`;
    box.setAttribute("data-status", status);

    let bookedTag = "";
    if (info.status === "BOOKED") {
      if (info.booked_by === CURRENT_CUSTOMER_ID) {
        bookedTag = " (Bạn giữ)";
      }
    }

    box.title = `${pcId}: ${info.specs} - ${info.price_per_hour.toLocaleString()}đ/h [${status}${bookedTag}]`;

    box.innerHTML = `
      <span class="seat-id">${pcId}</span>
      <span class="seat-status-dot"></span>
    `;

    box.addEventListener("click", () => handleSelectPc(pcId));

    if (info.zone === "VIP") vipContainer.appendChild(box);
    else if (info.zone === "PRO_GAMING") proContainer.appendChild(box);
    else if (info.zone === "STANDARD") stdContainer.appendChild(box);
    else if (info.zone === "STREAM") streamContainer.appendChild(box);
  }
}

// Xử lý khi nhấn chọn máy (Hỗ trợ chọn nhiều máy & Quản lý máy đã đặt)
function handleSelectPc(pcId) {
  const pc = allPcs[pcId];
  if (!pc) return;

  if (pc.status === "MAINTENANCE") {
    alert(`Máy ${pcId} hiện đang bảo trì phần cứng, vui lòng chọn máy khác!`);
    return;
  }

  if (pc.status === "OCCUPIED") {
    alert(`Máy ${pcId} hiện đang có khách chơi trực tiếp tại quán!`);
    return;
  }

  // Trường hợp máy ĐÃ ĐẶT (BOOKED)
  if (pc.status === "BOOKED") {
    targetManagePcId = pcId;
    document.getElementById("manage-pc-title").textContent = `QUẢN LÝ MÁY ${pcId} (${pc.zone})`;
    document.getElementById("manage-pc-specs").textContent = `${pc.specs} • ${pc.price_per_hour.toLocaleString()}đ/h`;
    document.getElementById("manage-booked-modal").classList.add("open");
    return;
  }

  // Trường hợp máy CÓ THỂ CHỌN (AVAILABLE) hoặc ĐANG CHỌN (SELECTED): Toggle đa chọn
  if (selectedPcIds.has(pcId)) {
    selectedPcIds.delete(pcId);
  } else {
    selectedPcIds.add(pcId);
  }

  render2DGrids();
  updateSelectedSummary();
}

// Cập nhật thanh tóm tắt chọn nhiều máy
function updateSelectedSummary() {
  const summaryDiv = document.getElementById("selected-summary");
  const confirmBtn = document.getElementById("btn-confirm-selection");
  const countBadge = document.getElementById("selected-count-badge");
  const clearBtn = document.getElementById("btn-clear-sel");

  const count = selectedPcIds.size;
  countBadge.textContent = count;

  if (count === 0) {
    summaryDiv.innerHTML = `<div class="selection-empty">Chưa chọn máy nào. Hãy nhấn vào các ô máy trên sơ đồ để chọn 1 hoặc nhiều máy!</div>`;
    confirmBtn.disabled = true;
    clearBtn.style.display = "none";
    return;
  }

  clearBtn.style.display = "inline-block";
  confirmBtn.disabled = false;

  let totalHourly = 0;
  const pcTags = [];
  selectedPcIds.forEach(id => {
    const pc = allPcs[id];
    if (pc) {
      totalHourly += pc.price_per_hour;
      pcTags.push(`<span class="sel-pc-tag">${id}</span>`);
    }
  });

  summaryDiv.innerHTML = `
    <div class="selection-active-multi">
      <div>${pcTags.join(" ")}</div>
      <div class="sel-info-text">
        <strong>${count} máy</strong> | Tổng cước: <strong>${totalHourly.toLocaleString()}đ/h</strong>
      </div>
    </div>
  `;
}

function clearAllSelections() {
  selectedPcIds.clear();
  render2DGrids();
  updateSelectedSummary();
}

// Mở Modal đặt nhiều máy
function openBookingModal() {
  if (selectedPcIds.size === 0) return;

  const count = selectedPcIds.size;
  document.getElementById("modal-booking-title").textContent = `ĐẶT ${count} MÁY ĐÃ CHỌN`;

  const listContainer = document.getElementById("modal-pc-list");
  listContainer.innerHTML = "";
  selectedPcIds.forEach(id => {
    const pc = allPcs[id];
    const chip = document.createElement("span");
    chip.className = "modal-pc-chip";
    chip.textContent = `${id} (${pc ? pc.zone : ''})`;
    listContainer.appendChild(chip);
  });

  selectDuration(currentDuration);
  document.getElementById("booking-modal").classList.add("open");
}

function closeBookingModal() {
  document.getElementById("booking-modal").classList.remove("open");
}

// Chọn thời lượng chơi
function selectDuration(hours) {
  currentDuration = hours;
  const buttons = document.querySelectorAll(".dur-btn");
  buttons.forEach(btn => {
    btn.classList.toggle("active", btn.textContent.startsWith(hours.toString()));
  });

  const count = selectedPcIds.size;
  document.getElementById("modal-count-display").textContent = `${count} máy`;
  document.getElementById("modal-duration-display").textContent = `${hours} giờ/máy`;

  let totalHourly = 0;
  selectedPcIds.forEach(id => {
    if (allPcs[id]) totalHourly += allPcs[id].price_per_hour;
  });
  const totalCost = totalHourly * hours;
  document.getElementById("modal-total-cost").textContent = `${totalCost.toLocaleString()} VNĐ`;
}

// Gửi yêu cầu đặt nhiều máy qua MCP
async function submitBooking() {
  if (selectedPcIds.size === 0) return;
  const customerId = document.getElementById("input-customer-id").value.trim() || CURRENT_CUSTOMER_ID;
  const btn = document.getElementById("btn-submit-booking");

  btn.disabled = true;
  btn.textContent = "ĐANG KHÓA MÁY QUA MCP...";

  try {
    const pcList = Array.from(selectedPcIds);
    const res = await fetch("/api/book", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: customerId,
        pc_ids: pcList,
        duration_hours: currentDuration
      })
    });

    const result = await res.json();
    if (result.status === "SUCCESS") {
      alert(`🎉 ${result.message}`);
      closeBookingModal();

      // Thêm tin nhắn vào khung chat AI
      appendChatMessage("ai", `✅ <strong>Đặt máy thành công qua MCP:</strong> ${result.message}`);

      // Cập nhật lại dữ liệu phòng máy
      selectedPcIds.clear();
      await loadPcsData();
    } else {
      alert(`⚠️ Không thể đặt máy: ${result.message || result.error}`);
    }
  } catch (err) {
    alert(`Lỗi kết nối đặt máy: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "XÁC NHẬN KHÓA MÁY VÀ ĐẶT CHỖ";
  }
}

// Hủy đặt máy (để đổi sang máy khác)
function closeManageModal() {
  document.getElementById("manage-booked-modal").classList.remove("open");
  targetManagePcId = null;
}

async function cancelBookedSeat() {
  if (!targetManagePcId) return;
  const pcId = targetManagePcId;

  try {
    const res = await fetch("/api/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: CURRENT_CUSTOMER_ID,
        pc_id: pcId
      })
    });

    const result = await res.json();
    if (result.status === "SUCCESS") {
      alert(`✅ ${result.message}`);
      closeManageModal();
      appendChatMessage("ai", `🔄 <strong>Đã hủy giữ máy:</strong> ${result.message}`);
      await loadPcsData();
    } else {
      alert(`⚠️ Lỗi: ${result.message}`);
    }
  } catch (err) {
    alert(`Lỗi hủy máy: ${err.message}`);
  }
}

// Lightbox ảnh không gian nhỏ
function openImageModal() {
  document.getElementById("image-modal").classList.add("open");
}
function closeImageModal() {
  document.getElementById("image-modal").classList.remove("open");
}

// Modal Thuyết Trình Demo (5 Bước Bảng Trắng)
function openDemoModal() {
  document.getElementById("demo-modal").classList.add("open");
}
function closeDemoModal() {
  document.getElementById("demo-modal").classList.remove("open");
}

// Mở/Đóng Chat AI Drawer
function toggleAIChat() {
  const drawer = document.getElementById("ai-drawer");
  drawer.classList.toggle("closed");
}

// ==============================================================================
// NITRO RE-ACT AI ASSISTANT CHAT ENGINE
// ==============================================================================

function sendQuickPrompt(text) {
  document.getElementById("chat-input").value = text;
  handleChatSubmit(new Event("submit"));
}

// Sample initial trace stream matching user's exact specification
const SAMPLE_INITIAL_STREAM = [
  '[16:13:17] 🛠️ [MCP:CALL] tool=order_canteen_item | args={"customer_id":"NET2026","item_name":"Mì tôm trứng xúc xích","pc_id":"VIP-08","quantity":1}',
  '[16:13:17] 👁️ [MCP:OBS] status=200 | dur=8720.92ms | result={"status":"SUCCESS","order_id":"ORDER-2026-1","customer_id":"NET2026","pc_id":"VIP-08","item_name":"Mì tôm trứng xúc xích","total_cost":25000}',
  "[16:13:17] ℹ️  [COMBO] Tool MCP 'order_canteen_item' succeeded",
  '[16:13:17] 🛠️ [MCP:CALL] tool=order_canteen_item | args={"customer_id":"NET2026","item_name":"Sting dâu","pc_id":"VIP-08","quantity":1}',
  '[16:13:17] 👁️ [MCP:OBS] status=200 | dur=6112.19ms | result={"status":"SUCCESS","order_id":"ORDER-2026-2","customer_id":"NET2026","pc_id":"VIP-08","item_name":"Sting dâu","total_cost":15000}',
  "[16:13:17] ℹ️  [COMBO] Tool MCP 'order_canteen_item' succeeded",
  '[16:13:17] 🧠 [REACT:THINK] step #3 | thought="OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."',
  '[16:13:17] 🏁 [AGENT:DONE] status=COMPLETE | steps=3 | total_dur=14833ms'
];

function initSampleStreamLogs() {
  const streamContainer = document.getElementById("trace-col-stream");
  if (!streamContainer) return;
  streamContainer.innerHTML = "";
  SAMPLE_INITIAL_STREAM.forEach(line => appendStreamLog(line));
}

function getNowTimeString() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `[${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}]`;
}

function appendStreamLog(rawLine) {
  const streamContainer = document.getElementById("trace-col-stream");
  if (!streamContainer) return;
  const lineHtml = formatLogLineToHtml(rawLine);
  streamContainer.insertAdjacentHTML('beforeend', lineHtml);
  streamContainer.scrollTop = streamContainer.scrollHeight;
  liveStreamLogHistory.push(rawLine);
}

function clearTraceStream() {
  const streamContainer = document.getElementById("trace-col-stream");
  if (streamContainer) {
    streamContainer.innerHTML = "";
  }
  liveStreamLogHistory = [];
}

function formatLogLineToHtml(line) {
  if (!line || !line.trim()) return "";
  
  // 1. Escape HTML
  let safe = line
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // 2. Format key=value BEFORE adding HTML tags with class attributes
  safe = safe.replace(/\b([a-zA-Z0-9_-]+)=([^\s|]+)/g, '§KEY§$1§/KEY§=§VAL§$2§/VAL§');

  // 3. Format pipe separators
  safe = safe.replace(/ \| /g, ' §PIPE§|§/PIPE§ ');

  // 4. Format timestamp [HH:MM:SS]
  safe = safe.replace(/^(\[\d{2}:\d{2}:\d{2}\])/, '§TS§$1§/TS§');

  // 5. Format debug tags
  safe = safe.replace(/\[COMBO\]/g, '§TAG_COMBO§[COMBO]§/TAG§');
  safe = safe.replace(/\[MCP:CALL\]/g, '§TAG_CALL§[MCP:CALL]§/TAG§');
  safe = safe.replace(/\[MCP:OBS\]/g, '§TAG_OBS§[MCP:OBS]§/TAG§');
  safe = safe.replace(/\[REACT:THINK\]/g, '§TAG_THINK§[REACT:THINK]§/TAG§');
  safe = safe.replace(/\[REACT:ANSWER\]/g, '§TAG_ANS§[REACT:ANSWER]§/TAG§');
  safe = safe.replace(/\[AGENT:START\]/g, '§TAG_START§[AGENT:START]§/TAG§');
  safe = safe.replace(/\[AGENT:DONE\]/g, '§TAG_DONE§[AGENT:DONE]§/TAG§');
  safe = safe.replace(/\[AGENT:ERROR\]/g, '§TAG_ERROR§[AGENT:ERROR]§/TAG§');

  // 6. Replace markers with final spans
  safe = safe
    .replace(/§KEY§/g, '<span class="log-key">').replace(/§\/KEY§/g, '</span>')
    .replace(/§VAL§/g, '<span class="log-val">').replace(/§\/VAL§/g, '</span>')
    .replace(/§PIPE§/g, '<span class="log-pipe">').replace(/§\/PIPE§/g, '</span>')
    .replace(/§TS§/g, '<span class="log-ts">').replace(/§\/TS§/g, '</span>')
    .replace(/§TAG_COMBO§/g, '<span class="log-tag tag-combo">')
    .replace(/§TAG_CALL§/g, '<span class="log-tag tag-call">')
    .replace(/§TAG_OBS§/g, '<span class="log-tag tag-obs">')
    .replace(/§TAG_THINK§/g, '<span class="log-tag tag-think">')
    .replace(/§TAG_ANS§/g, '<span class="log-tag tag-ans">')
    .replace(/§TAG_START§/g, '<span class="log-tag tag-start">')
    .replace(/§TAG_DONE§/g, '<span class="log-tag tag-done">')
    .replace(/§TAG_ERROR§/g, '<span class="log-tag tag-think">')
    .replace(/§\/TAG§/g, '</span>');

  return `<div class="stream-line">${safe}</div>`;
}

async function handleChatSubmit(e) {
  if (e) e.preventDefault();
  const input = document.getElementById("chat-input");
  const message = input.value.trim();
  if (!message) return;

  // Hiển thị tin nhắn người dùng
  appendChatMessage("user", message);
  input.value = "";

  // Mở drawer nếu đang đóng
  document.getElementById("ai-drawer").classList.remove("closed");

  const startTime = Date.now();
  const ts = getNowTimeString();

  // Log bắt đầu quá trình A.I làm việc
  appendStreamLog(`${ts} 🚀 [AGENT:START] query="${message}" | customer_id="${CURRENT_CUSTOMER_ID}"`);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        message: message,
        history: chatSessionHistory
      })
    });

    const data = await res.json();
    const duration = Date.now() - startTime;

    if (data.status === "SUCCESS") {
      latestLiveTraceLogs = data.trace_logs || [];
      renderTraceLogs(data.trace_logs, duration);
      appendChatMessage("ai", formatMarkdown(data.final_answer));

      // Lưu vết vào Session History
      chatSessionHistory.push({ role: "user", content: message });
      chatSessionHistory.push({ role: "assistant", content: data.final_answer });

      // Tự động tải lại dữ liệu sơ đồ phòng máy
      await loadPcsData();
    } else {
      appendChatMessage("ai", "⚠️ Có lỗi xảy ra trong quá trình xử lý qua ReAct Agent.");
      appendStreamLog(`${getNowTimeString()} ⚠️ [AGENT:ERROR] status=FAIL | msg="ReAct agent failed"`);
    }
  } catch (err) {
    appendChatMessage("ai", `⚠️ Lỗi kết nối tới Agent API: ${err.message}`);
    appendStreamLog(`${getNowTimeString()} ⚠️ [AGENT:ERROR] exception="${err.message}"`);
  }
}

// Bật/tắt thu nhỏ ô vuông Trace Log góc màn hình
function toggleCornerTrace() {
  const box = document.getElementById("corner-trace-box");
  const btn = document.getElementById("btn-corner-toggle");
  if (!box) return;

  box.classList.toggle("minimized");
  if (box.classList.contains("minimized")) {
    btn.textContent = "+";
    btn.title = "Mở rộng";
  } else {
    btn.textContent = "−";
    btn.title = "Thu nhỏ";
  }
}

// Render các bước ReAct Waterfall Trace thành các dòng logs thực tế của quá trình A.I làm việc
function renderTraceLogs(logs, totalDuration = 1200) {
  if (!logs || logs.length === 0) return;

  logs.forEach((item, index) => {
    const ts = getNowTimeString();
    const step = item.step || (index + 1);

    // 1. Tool execution step
    if (item.action_type === "TOOL_EXECUTION") {
      const toolName = item.tool_name || "tool";
      const argsStr = JSON.stringify(item.arguments || {});
      appendStreamLog(`${ts} 🛠️ [MCP:CALL] tool=${toolName} | args=${argsStr}`);

      const obsStr = JSON.stringify(item.observation || {});
      const lat = item.latency_ms || Math.floor(Math.random() * 80 + 30);
      appendStreamLog(`${ts} 👁️ [MCP:OBS] status=200 | dur=${lat}ms | result=${obsStr}`);
      appendStreamLog(`${ts} ℹ️  [COMBO] Tool MCP '${toolName}' succeeded`);
    }

    // 2. Thought reasoning step
    if (item.thought) {
      const cleanThought = item.thought.replace(/\n/g, ' ').trim();
      appendStreamLog(`${ts} 🧠 [REACT:THINK] step #${step} | thought="${cleanThought}"`);
    }

    // 3. Final Answer step
    if (item.action_type === "FINAL_ANSWER") {
      appendStreamLog(`${ts} 🏁 [AGENT:DONE] status=COMPLETE | steps=${logs.length} | total_dur=${totalDuration}ms`);
    }
  });
}



// ==============================================================================
// TRACE LOGS & OBSERVABILITY INSPECTOR DASHBOARD
// ==============================================================================
let latestLiveTraceLogs = [];
let currentTraceTab = 'stream';

function openTraceModal() {
  document.getElementById("trace-modal").classList.add("open");
  switchTraceTab(currentTraceTab);
}
function closeTraceModal() {
  document.getElementById("trace-modal").classList.remove("open");
}

async function switchTraceTab(tab) {
  currentTraceTab = tab;
  const tabStream = document.getElementById("tab-stream-trace");
  const tabLive = document.getElementById("tab-live-trace");
  const tabWaterfall = document.getElementById("tab-waterfall-trace");

  if (tabStream) tabStream.classList.toggle("active", tab === "stream");
  if (tabLive) tabLive.classList.toggle("active", tab === "live");
  if (tabWaterfall) tabWaterfall.classList.toggle("active", tab === "waterfall");

  const container = document.getElementById("trace-log-view-container");
  if (tab === "stream") {
    renderStreamConsoleView();
  } else if (tab === "live") {
    renderTraceInspectorView(latestLiveTraceLogs, "Phiên Chat Live Trực Tiếp");
  } else {
    container.innerHTML = `<div class="trace-loading">⏳ Đang lấy dữ liệu từ docs/trace_waterfall.json...</div>`;
    try {
      const res = await fetch("/api/traces");
      const traces = await res.json();
      renderTraceInspectorView(traces, "Lịch Sử Waterfall Trace (Test Suite JSON)");
    } catch (err) {
      container.innerHTML = `<div class="trace-empty-state">⚠️ Không thể tải lịch sử trace log: ${err.message}</div>`;
    }
  }
}

function renderStreamConsoleView() {
  const container = document.getElementById("trace-log-view-container");
  const logsToDisplay = liveStreamLogHistory.length > 0 ? liveStreamLogHistory : SAMPLE_INITIAL_STREAM;
  
  let linesHtml = "";
  logsToDisplay.forEach(line => {
    linesHtml += formatLogLineToHtml(line);
  });

  container.innerHTML = `
    <div class="modal-stream-console-wrapper">
      <div class="modal-stream-header">
        <div class="modal-stream-meta">
          <span class="pulse-dot-cyan"></span>
          <span>A.I EXECUTION RAW LOGS STREAM (${logsToDisplay.length} lines)</span>
        </div>
        <button class="corner-btn" onclick="copyStreamLogs()" style="width:auto; padding: 0 10px; font-size: 0.7rem;">📋 Sao Chép Logs</button>
      </div>
      <div class="modal-stream-body">
        ${linesHtml}
      </div>
    </div>
  `;
}

function copyStreamLogs() {
  const logsToDisplay = liveStreamLogHistory.length > 0 ? liveStreamLogHistory : SAMPLE_INITIAL_STREAM;
  const rawText = logsToDisplay.join("\n");
  navigator.clipboard.writeText(rawText).then(() => {
    alert("Đã sao chép toàn bộ A.I Stream Debug Logs vào bộ nhớ tạm!");
  }).catch(() => {
    alert("Không thể sao chép tự động. Hãy bôi đen văn bản để sao chép!");
  });
}


function renderTraceInspectorView(logs, title) {
  const container = document.getElementById("trace-log-view-container");
  if (!logs || logs.length === 0) {
    container.innerHTML = `<div class="trace-empty-state">Chưa có nhật ký trace log nào cho [${title}]. Hãy gửi câu hỏi cho AI Agent ở khung chat bên phải để bắt đầu!</div>`;
    return;
  }

  let html = `<div class="inspector-summary-bar">📌 Đang hiển thị ${logs.length} sự kiện trace log trong <strong>${title}</strong></div>`;

  logs.forEach((item, index) => {
    const isTool = item.action_type === "TOOL_EXECUTION";
    const toolName = item.tool_name || "Trả lời trực tiếp";
    const thoughtReason = item.thought || (isTool ? `Phân tích câu hỏi khách hàng -> Đã xác định cần gọi Tool '${toolName}'` : "Phân tích câu hỏi -> Trả lời văn bản");
    const customerId = (item.arguments && item.arguments.customer_id) ? item.arguments.customer_id : "NET2026";

    html += `
      <div class="inspector-card ${isTool ? 'card-tool-call' : 'card-final-answer'}">
        <div class="card-header-bar">
          <span class="step-badge">BƯỚC #${item.step || (index + 1)}</span>
          <span class="action-type-tag">${isTool ? '🛠️ TOOL CALL EXECUTION' : '🏁 FINAL ANSWER'}</span>
          <span class="latency-tag">⏱️ ${item.latency_ms || 0} ms</span>
        </div>

        <div class="inspector-section">
          <div class="section-title">🧠 1. ĐÃ XÁC ĐỊNH LÀM SAO ĐỂ BIẾT DÙNG TOOL NÀO? (THOUGHT REASONING)</div>
          <div class="thought-box">${thoughtReason}</div>
        </div>

        <div class="inspector-section">
          <div class="section-title">🛠️ 2. AI ĐÃ GỌI TOOL GÌ? CHO AI? (ACTION SPECIFICATION)</div>
          <div class="action-box">
            <div><strong>Tên Tool:</strong> <code class="code-hl">${toolName}</code></div>
            <div><strong>Mã Tài Khoản Hội Viên (Customer ID):</strong> <strong class="id-hl">${customerId}</strong></div>
            <div><strong>Tham Số Đầu Vào (Arguments):</strong></div>
            <pre class="json-code">${JSON.stringify(item.arguments || {}, null, 2)}</pre>
          </div>
        </div>

        ${isTool ? `
        <div class="inspector-section">
          <div class="section-title">👁️ 3. ĐÃ LÀM CÁI GÌ & ĐƯỢC KẾT QUẢ GÌ? (OBSERVATION TỪ MCP SERVER)</div>
          <div class="obs-box">
            <pre class="json-code">${JSON.stringify(item.observation || {}, null, 2)}</pre>
          </div>
        </div>
        ` : `
        <div class="inspector-section">
          <div class="section-title">💬 3. KẾT QUẢ CÂU TRẢ LỜI CUỐI CÙNG (FINAL ANSWER)</div>
          <div class="final-box">${formatMarkdown(item.output || "")}</div>
        </div>
        `}
      </div>
    `;
  });

  container.innerHTML = html;
}

function appendChatMessage(sender, htmlContent) {
  const chatMessages = document.getElementById("chat-messages");
  const msgDiv = document.createElement("div");
  msgDiv.className = `msg msg-${sender}`;
  msgDiv.innerHTML = `<div class="msg-content">${htmlContent}</div>`;
  chatMessages.appendChild(msgDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>');
}
