/* ============================================================
   ExpenseAI frontend
   Talks to the Flask API in server.py. No business logic here —
   this only renders whatever the backend (your existing OCR /
   SQLite / Ollama pipeline) returns.
   ============================================================ */

const API = "";

// ------------------------------------------------------------
// Routing
// ------------------------------------------------------------

function goto(page) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("is-active"));
  document.querySelectorAll(".rail-link").forEach(l => l.classList.remove("is-active"));
  document.getElementById(`page-${page}`).classList.add("is-active");
  document.querySelector(`.rail-link[data-page="${page}"]`).classList.add("is-active");
  window.location.hash = page;

  if (page === "dashboard") loadDashboard();
  if (page === "expenses") loadExpenseFilters().then(loadExpenses);
}

document.querySelectorAll(".rail-link").forEach(link => {
  link.addEventListener("click", () => goto(link.dataset.page));
});
document.querySelectorAll("[data-goto]").forEach(el => {
  el.addEventListener("click", () => goto(el.dataset.goto));
});

window.addEventListener("DOMContentLoaded", () => {
  const initial = window.location.hash.replace("#", "") || "home";
  if (document.getElementById(`page-${initial}`)) goto(initial);
});

// ------------------------------------------------------------
// Small helpers
// ------------------------------------------------------------

function fmtMoney(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}

function fmtNum(n) {
  if (n === null || n === undefined) return "—";
  return Number(n).toLocaleString("en-IN");
}

function isNumericColumn(name) {
  return /amount|total|price|qty|quantity/i.test(name);
}

async function getJSON(url) {
  const res = await fetch(url);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// ============================================================
// DASHBOARD
// ============================================================

let categoryChart = null;
let trendChart = null;

async function loadDashboard() {
  const emptyEl = document.getElementById("dashboard-empty");
  const contentEl = document.getElementById("dashboard-content");
  try {
    const data = await getJSON(`${API}/api/dashboard`);
    if (!data.has_data) {
      emptyEl.hidden = false;
      contentEl.hidden = true;
      return;
    }
    emptyEl.hidden = true;
    contentEl.hidden = false;

    const kpis = [];
    kpis.push({ label: "Total records", value: fmtNum(data.total_records) });
    if (data.total_invoices !== undefined) kpis.push({ label: "Invoices", value: fmtNum(data.total_invoices) });
    if (data.total_categories !== undefined) kpis.push({ label: "Categories", value: fmtNum(data.total_categories) });
    if (data.total_amount !== undefined && data.total_amount !== null) kpis.push({ label: "Total amount", value: fmtMoney(data.total_amount) });
    if (data.avg_amount !== undefined && data.avg_amount !== null) kpis.push({ label: "Average expense", value: fmtMoney(data.avg_amount) });

    document.getElementById("kpi-strip").innerHTML = kpis.map(k => `
      <div class="kpi">
        <p class="kpi-label">${k.label}</p>
        <p class="kpi-value">${k.value}</p>
      </div>
    `).join("");

    renderCategoryChart(data.by_category || []);
    renderTrendChart(data.trend || []);
  } catch (e) {
    emptyEl.hidden = false;
    contentEl.hidden = true;
    emptyEl.querySelector("h3").textContent = "Couldn't load the dashboard";
    emptyEl.querySelector("p").textContent = e.message;
  }
}

function chartColors() {
  return { ink: "#16232f", grid: "#dfdcd2", emerald: "#1f6f56", amber: "#b9812f" };
}

function renderCategoryChart(rows) {
  const canvas = document.getElementById("chart-category");
  const emptyEl = document.getElementById("chart-category-empty");
  if (categoryChart) { categoryChart.destroy(); categoryChart = null; }
  if (!rows.length) { canvas.style.display = "none"; emptyEl.hidden = false; return; }
  canvas.style.display = "block"; emptyEl.hidden = true;
  const c = chartColors();
  categoryChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: rows.map(r => r.category),
      datasets: [{ data: rows.map(r => r.amount), backgroundColor: c.emerald, borderRadius: 3, maxBarThickness: 34 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => fmtMoney(ctx.parsed.y) } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: c.ink, font: { family: "Inter", size: 11 } } },
        y: { grid: { color: c.grid }, ticks: { color: c.ink, font: { family: "IBM Plex Mono", size: 10 } } },
      },
    },
  });
}

function renderTrendChart(rows) {
  const canvas = document.getElementById("chart-trend");
  const emptyEl = document.getElementById("chart-trend-empty");
  if (trendChart) { trendChart.destroy(); trendChart = null; }
  if (!rows.length) { canvas.style.display = "none"; emptyEl.hidden = false; return; }
  canvas.style.display = "block"; emptyEl.hidden = true;
  const c = chartColors();
  trendChart = new Chart(canvas, {
    type: "line",
    data: {
      labels: rows.map(r => r.date),
      datasets: [{
        data: rows.map(r => r.amount),
        borderColor: c.emerald, backgroundColor: "rgba(31,111,86,0.08)",
        fill: true, tension: 0.25, pointRadius: 2,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => fmtMoney(ctx.parsed.y) } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: c.ink, font: { family: "Inter", size: 10 }, maxRotation: 0, autoSkip: true } },
        y: { grid: { color: c.grid }, ticks: { color: c.ink, font: { family: "IBM Plex Mono", size: 10 } } },
      },
    },
  });
}

document.getElementById("dashboard-refresh").addEventListener("click", loadDashboard);

// ============================================================
// EXPENSES
// ============================================================

const expenseFilters = { category: new Set(), invoice: new Set(), search: "", dateFrom: "", dateTo: "" };

async function loadExpenseFilters() {
  try {
    const data = await getJSON(`${API}/api/expenses/filters`);

    const catWrap = document.getElementById("filter-category-wrap");
    const invWrap = document.getElementById("filter-invoice-wrap");
    const dateWrap = document.getElementById("filter-dates-wrap");

    if (data.categories.length) {
      catWrap.hidden = false;
      document.getElementById("filter-category-menu").innerHTML = data.categories.map(c => `
        <label class="filter-option"><input type="checkbox" value="${escapeHtml(c)}" data-filter="category"> ${escapeHtml(c)}</label>
      `).join("");
    } else { catWrap.hidden = true; }

    if (data.invoices.length) {
      invWrap.hidden = false;
      document.getElementById("filter-invoice-menu").innerHTML = data.invoices.map(i => `
        <label class="filter-option"><input type="checkbox" value="${escapeHtml(i)}" data-filter="invoice"> ${escapeHtml(i)}</label>
      `).join("");
    } else { invWrap.hidden = true; }

    dateWrap.hidden = !data.has_dates;
  } catch (e) {
    // Filters are optional embellishment; table load will surface real errors.
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
}

function toggleMenu(menuId, btnId) {
  const menu = document.getElementById(menuId);
  const isOpen = menu.classList.contains("is-open");
  document.querySelectorAll(".filter-select-menu").forEach(m => m.classList.remove("is-open"));
  if (!isOpen) menu.classList.add("is-open");
}
document.getElementById("filter-category-btn").addEventListener("click", (e) => {
  e.stopPropagation(); toggleMenu("filter-category-menu", "filter-category-btn");
});
document.getElementById("filter-invoice-btn").addEventListener("click", (e) => {
  e.stopPropagation(); toggleMenu("filter-invoice-menu", "filter-invoice-btn");
});
document.addEventListener("click", () => document.querySelectorAll(".filter-select-menu").forEach(m => m.classList.remove("is-open")));

document.getElementById("filter-category-menu").addEventListener("change", (e) => {
  if (e.target.dataset.filter !== "category") return;
  e.target.checked ? expenseFilters.category.add(e.target.value) : expenseFilters.category.delete(e.target.value);
  document.getElementById("filter-category-count").textContent = expenseFilters.category.size ? `(${expenseFilters.category.size})` : "";
  loadExpenses();
});
document.getElementById("filter-invoice-menu").addEventListener("change", (e) => {
  if (e.target.dataset.filter !== "invoice") return;
  e.target.checked ? expenseFilters.invoice.add(e.target.value) : expenseFilters.invoice.delete(e.target.value);
  document.getElementById("filter-invoice-count").textContent = expenseFilters.invoice.size ? `(${expenseFilters.invoice.size})` : "";
  loadExpenses();
});

let searchDebounce = null;
document.getElementById("filter-search").addEventListener("input", (e) => {
  expenseFilters.search = e.target.value;
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadExpenses, 250);
});

document.getElementById("filter-date-from").addEventListener("change", (e) => { expenseFilters.dateFrom = e.target.value; loadExpenses(); });
document.getElementById("filter-date-to").addEventListener("change", (e) => { expenseFilters.dateTo = e.target.value; loadExpenses(); });

document.getElementById("filter-clear").addEventListener("click", () => {
  expenseFilters.category.clear(); expenseFilters.invoice.clear();
  expenseFilters.search = ""; expenseFilters.dateFrom = ""; expenseFilters.dateTo = "";
  document.getElementById("filter-search").value = "";
  document.getElementById("filter-date-from").value = "";
  document.getElementById("filter-date-to").value = "";
  document.querySelectorAll('.filter-select-menu input[type="checkbox"]').forEach(cb => cb.checked = false);
  document.getElementById("filter-category-count").textContent = "";
  document.getElementById("filter-invoice-count").textContent = "";
  loadExpenses();
});

async function loadExpenses() {
  const params = new URLSearchParams();
  if (expenseFilters.category.size) params.set("category", [...expenseFilters.category].join("|"));
  if (expenseFilters.invoice.size) params.set("invoice", [...expenseFilters.invoice].join("|"));
  if (expenseFilters.search) params.set("search", expenseFilters.search);
  if (expenseFilters.dateFrom) params.set("date_from", expenseFilters.dateFrom);
  if (expenseFilters.dateTo) params.set("date_to", expenseFilters.dateTo);

  const emptyEl = document.getElementById("expenses-empty");
  const tableWrap = document.getElementById("expenses-table-wrap");
  const countEl = document.getElementById("expenses-count");

  try {
    const data = await getJSON(`${API}/api/expenses?${params.toString()}`);
    if (!data.has_data || data.total === 0) {
      emptyEl.hidden = false; tableWrap.hidden = true; countEl.textContent = "";
      return;
    }
    emptyEl.hidden = true; tableWrap.hidden = false;
    countEl.textContent = `Showing ${data.count} of ${data.total} record${data.total === 1 ? "" : "s"}`;

    document.getElementById("expenses-thead-row").innerHTML =
      data.columns.map(c => `<th>${escapeHtml(c)}</th>`).join("");

    document.getElementById("expenses-tbody").innerHTML = data.records.map(row => `
      <tr>${data.columns.map(c => {
        const v = row[c];
        const numeric = isNumericColumn(c);
        const display = v === null || v === undefined || v === "" ? "—" : (numeric && !Number.isNaN(Number(v)) ? fmtMoney(v) : escapeHtml(v));
        return `<td class="${numeric ? "num" : ""}">${display}</td>`;
      }).join("")}</tr>
    `).join("");
  } catch (e) {
    emptyEl.hidden = false; tableWrap.hidden = true; countEl.textContent = "";
    emptyEl.querySelector("h3").textContent = "Couldn't load expenses";
    emptyEl.querySelector("p").textContent = e.message;
  }
}

// ============================================================
// UPLOAD BILLS
// ============================================================

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const processBtn = document.getElementById("process-btn");
const pipelineStatus = document.getElementById("pipeline-status");
const uploadLog = document.getElementById("upload-log");

let pendingFilename = null;

["dragenter", "dragover"].forEach(evt => {
  dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add("is-dragover"); });
});
["dragleave", "drop"].forEach(evt => {
  dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove("is-dragover"); });
});
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelected(file);
});
fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) handleFileSelected(file);
});

function logLine(text, kind) {
  const div = document.createElement("div");
  div.className = "log-line" + (kind ? ` is-${kind}` : "");
  div.textContent = text;
  uploadLog.prepend(div);
}

function resetPipelineUI() {
  document.querySelectorAll("#pipeline-steps li").forEach(li => li.classList.remove("is-running", "is-done", "is-error"));
}

async function handleFileSelected(file) {
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (![".jpg", ".jpeg", ".png", ".pdf"].includes(ext)) {
    logLine(`Unsupported file type: ${file.name}`, "error");
    return;
  }
  resetPipelineUI();
  pipelineStatus.textContent = `Uploading ${file.name}…`;
  processBtn.disabled = true;
  pendingFilename = null;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API}/api/upload`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");
    pendingFilename = data.filename;
    pipelineStatus.textContent = `Saved as ${data.filename}. Ready to process.`;
    logLine(`Uploaded ${data.filename}`, "success");
    processBtn.disabled = false;
  } catch (e) {
    pipelineStatus.textContent = "Upload failed.";
    logLine(e.message, "error");
  }
}

processBtn.addEventListener("click", async () => {
  if (!pendingFilename) return;
  processBtn.disabled = true;
  resetPipelineUI();
  pipelineStatus.textContent = "Starting pipeline…";

  try {
    const { job_id } = await postJSON(`${API}/api/process`, { filename: pendingFilename });
    pollJob(job_id);
  } catch (e) {
    pipelineStatus.textContent = "Couldn't start processing.";
    logLine(e.message, "error");
    processBtn.disabled = false;
  }
});

const STEP_LABELS = {
  convert: "Preparing file",
  clean: "Cleaning image",
  ocr: "Running OCR",
  extract: "Extracting with AI",
  save: "Saving to database",
};

function pollJob(jobId) {
  const poll = async () => {
    try {
      const job = await getJSON(`${API}/api/process/status/${jobId}`);

      Object.entries(job.steps).forEach(([step, status]) => {
        const li = document.querySelector(`#pipeline-steps li[data-step="${step}"]`);
        if (!li) return;
        li.classList.remove("is-running", "is-done", "is-error");
        if (status === "running") li.classList.add("is-running");
        if (status === "done") li.classList.add("is-done");
        if (status === "error") li.classList.add("is-error");
      });

      const runningStep = Object.entries(job.steps).find(([, s]) => s === "running");
      if (job.status === "running") {
        pipelineStatus.textContent = runningStep ? `${STEP_LABELS[runningStep[0]]}…` : "Working…";
        setTimeout(poll, 900);
      } else if (job.status === "success") {
        pipelineStatus.textContent = "Bill processed and saved to the database.";
        logLine("Bill processed and saved to the database.", "success");
        processBtn.disabled = true;
        pendingFilename = null;
      } else {
        pipelineStatus.textContent = "Processing failed.";
        logLine(job.message || "Something went wrong while processing the bill.", "error");
        processBtn.disabled = false;
      }
    } catch (e) {
      pipelineStatus.textContent = "Lost track of the job.";
      logLine(e.message, "error");
      processBtn.disabled = false;
    }
  };
  poll();
}

// ============================================================
// AI ASSISTANT
// ============================================================

const chatMessages = document.getElementById("chat-messages");
const chatEmpty = document.getElementById("chat-empty");
const chatScroll = document.getElementById("chat-scroll");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");

function scrollChatToBottom() {
  chatScroll.scrollTop = chatScroll.scrollHeight;
}

function addUserMessage(text) {
  chatEmpty.hidden = true;
  const div = document.createElement("div");
  div.className = "msg msg-user";
  div.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
  chatMessages.appendChild(div);
  scrollChatToBottom();
}

function addTypingIndicator() {
  const div = document.createElement("div");
  div.className = "msg msg-assistant";
  div.id = "typing-indicator";
  div.innerHTML = `<div class="msg-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>`;
  chatMessages.appendChild(div);
  scrollChatToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

function addAssistantMessage({ text, sql, columns, rows, isError }) {
  const div = document.createElement("div");
  div.className = "msg msg-assistant" + (isError ? " is-error" : "");
  let html = `<div class="msg-bubble">${escapeHtml(text)}`;
  if (sql) html += `<div class="msg-sql">${escapeHtml(sql)}</div>`;
  if (columns && columns.length) {
    html += `<div class="msg-table-wrap"><table class="msg-table"><thead><tr>${columns.map(c => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead><tbody>`;
    rows.forEach(row => {
      html += `<tr>${columns.map(c => {
        const v = row[c];
        const numeric = isNumericColumn(c);
        const display = v === null || v === undefined || v === "" ? "—" : (numeric && !Number.isNaN(Number(v)) ? fmtMoney(v) : escapeHtml(v));
        return `<td>${display}</td>`;
      }).join("")}</tr>`;
    });
    html += `</tbody></table></div>`;
  }
  html += `</div>`;
  div.innerHTML = html;
  chatMessages.appendChild(div);
  scrollChatToBottom();
}

async function askQuestion(question) {
  addUserMessage(question);
  chatInput.value = "";
  chatSend.disabled = true;
  addTypingIndicator();

  try {
    const data = await postJSON(`${API}/api/chat`, { question });
    removeTypingIndicator();
    if (data.empty) {
      addAssistantMessage({ text: "I couldn't find any matching records in the database.", sql: data.sql });
    } else {
      addAssistantMessage({
        text: `Found ${data.rows.length} record${data.rows.length === 1 ? "" : "s"}.`,
        sql: data.sql, columns: data.columns, rows: data.rows,
      });
    }
  } catch (e) {
    removeTypingIndicator();
    addAssistantMessage({ text: e.message, isError: true });
  } finally {
    chatSend.disabled = false;
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = chatInput.value.trim();
  if (!q) return;
  askQuestion(q);
});

document.querySelectorAll(".suggestion").forEach(btn => {
  btn.addEventListener("click", () => askQuestion(btn.textContent));
});

document.getElementById("chat-clear").addEventListener("click", () => {
  chatMessages.innerHTML = "";
  chatEmpty.hidden = false;
});
