const state = {
  cases: [],
  selected: null,
  lastResponse: null,
};

const fields = [
  "id",
  "enabled",
  "endpoint",
  "category",
  "input_type",
  "source",
  "mode",
  "strategy",
  "payload_or_file",
  "expected_status",
  "expected_checks",
  "description",
  "expected_nl",
  "manual_conclusion",
  "last_status",
  "last_run_at",
];

const form = document.getElementById("caseForm");
const caseList = document.getElementById("caseList");
const toast = document.getElementById("toast");

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.hidden = true;
  }, 2400);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json();
  if (!response.ok || body.error) {
    throw new Error(body.error || `HTTP ${response.status}`);
  }
  return body;
}

function currentCaseFromForm() {
  const data = {};
  const formData = new FormData(form);
  fields.forEach((field) => {
    data[field] = String(formData.get(field) || "");
  });
  return data;
}

function fillForm(item) {
  fields.forEach((field) => {
    const input = form.elements[field];
    if (input) {
      input.value = item[field] || "";
    }
  });
}

function selectCase(item) {
  state.selected = { ...item };
  fillForm(state.selected);
  renderList();
  document.getElementById("requestPreview").textContent = "";
  document.getElementById("responsePreview").textContent = "";
  document.getElementById("samplePreview").textContent = "";
  document.getElementById("checkList").innerHTML = "";
  updateStatus("尚未运行");
}

function currentTimestamp() {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
  ].join("-") + " " + [
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds()),
  ].join(":");
}

function caseMatchesFilters(item) {
  const endpoint = document.getElementById("endpointFilter").value;
  const enabled = document.getElementById("enabledFilter").value;
  const search = document.getElementById("searchInput").value.trim().toLowerCase();
  if (endpoint && item.endpoint !== endpoint) {
    return false;
  }
  if (enabled === "yes" && item.enabled !== "yes") {
    return false;
  }
  if (enabled === "no" && item.enabled === "yes") {
    return false;
  }
  if (!search) {
    return true;
  }
  const haystack = fields.map((field) => item[field] || "").join(" ").toLowerCase();
  return haystack.includes(search);
}

function renderList() {
  const items = state.cases.filter(caseMatchesFilters);
  caseList.innerHTML = "";
  items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "case-item";
    if (state.selected && item.id === state.selected.id && item.endpoint === state.selected.endpoint) {
      button.classList.add("active");
    }
    button.innerHTML = `
      <div class="case-id">
        <span>${escapeHtml(item.id || "(new)")}</span>
        <span class="case-status ${item.last_status === "通过" ? "pass" : item.last_status === "失败" ? "fail" : ""}">${escapeHtml(item.last_status || item.endpoint || "")}</span>
      </div>
      <div class="case-meta">${escapeHtml(item.description || "")}</div>
      <div class="case-meta">${escapeHtml(item.endpoint || "")} / ${escapeHtml(item.category || "")}</div>
    `;
    button.addEventListener("click", () => selectCase(item));
    caseList.appendChild(button);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function loadCases() {
  const data = await api("/api/cases");
  state.cases = data.cases || [];
  renderList();
  if (!state.selected && state.cases.length) {
    selectCase(state.cases[0]);
  } else if (state.selected) {
    const updated = state.cases.find((item) => item.id === state.selected.id && item.endpoint === state.selected.endpoint);
    if (updated) {
      selectCase(updated);
    }
  }
}

async function saveCase({ silent = false } = {}) {
  const data = await api("/api/cases/save", {
    method: "POST",
    body: JSON.stringify({ case: currentCaseFromForm() }),
  });
  state.cases = data.cases || [];
  selectCase(data.case);
  if (!silent) {
    showToast("已保存");
  }
  return data.case;
}

async function newCase(endpoint) {
  const data = await api("/api/cases/new", {
    method: "POST",
    body: JSON.stringify({ endpoint }),
  });
  state.cases = data.cases || [];
  selectCase(data.case);
  showToast("已新增");
}

async function duplicateCase() {
  const current = currentCaseFromForm();
  current.id = "";
  current.description = `${current.description || "测试用例"} 副本`;
  const data = await api("/api/cases/save", {
    method: "POST",
    body: JSON.stringify({ case: current }),
  });
  state.cases = data.cases || [];
  selectCase(data.case);
  showToast("已复制");
}

async function deleteCase() {
  const current = currentCaseFromForm();
  if (!current.id || !window.confirm(`删除 ${current.id}？`)) {
    return;
  }
  const data = await api("/api/cases/delete", {
    method: "POST",
    body: JSON.stringify({ id: current.id, endpoint: current.endpoint }),
  });
  state.cases = data.cases || [];
  state.selected = null;
  renderList();
  if (state.cases.length) {
    selectCase(state.cases[0]);
  }
  showToast("已删除");
}

async function runCase() {
  const saved = await saveCase({ silent: true });
  updateStatus("运行中...");
  const data = await api("/api/cases/run", {
    method: "POST",
    body: JSON.stringify({
      case: saved,
      base_url: document.getElementById("baseUrlInput").value.trim() || "http://127.0.0.1:4000",
    }),
  });
  state.lastResponse = data.response_body;
  state.selected = data.case;
  await loadCases();
  document.getElementById("requestPreview").textContent = JSON.stringify(data.request, null, 2);
  document.getElementById("responsePreview").textContent = JSON.stringify(data.response_body, null, 2);
  renderChecks(data);
  updateStatus(`HTTP ${data.status_code} / ${data.conclusion} / ${data.summary || ""}`, data.conclusion);
}

async function markConclusion(conclusion) {
  form.elements.last_status.value = conclusion ? conclusion : "";
  form.elements.last_run_at.value = conclusion ? currentTimestamp() : "";
  const saved = await saveCase({ silent: true });
  updateStatus(conclusion ? `已标记最近状态为${conclusion}` : "已清除最近状态", conclusion);
  showToast(conclusion ? `已标记状态${conclusion}` : "已清除状态");
  return saved;
}

async function toggleConclusion() {
  const current = form.elements.last_status.value.trim();
  const next = current === "通过" ? "失败" : "通过";
  return markConclusion(next);
}

function updateStatus(text, conclusion = "") {
  const box = document.getElementById("statusBox");
  box.textContent = text;
  box.classList.toggle("pass", conclusion === "通过");
  box.classList.toggle("fail", conclusion === "失败");
}

function renderChecks(data) {
  const checkList = document.getElementById("checkList");
  checkList.innerHTML = "";
  (data.passed_checks || []).forEach((text) => {
    checkList.appendChild(checkItem(text, "pass"));
  });
  (data.failed_checks || []).forEach((text) => {
    checkList.appendChild(checkItem(text, "fail"));
  });
}

function checkItem(text, type) {
  const item = document.createElement("div");
  item.className = `check-item ${type}`;
  item.textContent = text;
  return item;
}

async function loadSample() {
  const path = form.elements.payload_or_file.value.trim();
  if (!path.startsWith("tests/")) {
    showToast("只有 tests/ 下的样例文件可直接查看");
    return;
  }
  const data = await api(`/api/sample?path=${encodeURIComponent(path)}`);
  document.getElementById("samplePreview").textContent = data.content;
}

function formatResponseJson() {
  if (!state.lastResponse) {
    showToast("没有可格式化的响应");
    return;
  }
  document.getElementById("responsePreview").textContent = JSON.stringify(state.lastResponse, null, 2);
}

function makeContainsCheck() {
  const selection = String(window.getSelection() || "").trim();
  if (!selection) {
    showToast("先在响应 JSON 中选中一段文本");
    return;
  }
  const input = form.elements.expected_checks;
  const nextCheck = `contains=${selection.replaceAll(";", " ")}`;
  input.value = input.value.trim() ? `${input.value.trim()};${nextCheck}` : nextCheck;
  showToast("已添加 contains 检查");
}

["searchInput", "endpointFilter", "enabledFilter"].forEach((id) => {
  document.getElementById(id).addEventListener("input", renderList);
});

document.getElementById("reloadButton").addEventListener("click", () => loadCases().catch((error) => showToast(error.message)));
document.getElementById("saveButton").addEventListener("click", () => saveCase().catch((error) => showToast(error.message)));
document.getElementById("runButton").addEventListener("click", () => runCase().catch((error) => updateStatus(`运行失败：${error.message}`, "失败")));
document.getElementById("newRegisterButton").addEventListener("click", () => newCase("register").catch((error) => showToast(error.message)));
document.getElementById("newQueryButton").addEventListener("click", () => newCase("query").catch((error) => showToast(error.message)));
document.getElementById("duplicateButton").addEventListener("click", () => duplicateCase().catch((error) => showToast(error.message)));
document.getElementById("deleteButton").addEventListener("click", () => deleteCase().catch((error) => showToast(error.message)));
document.getElementById("loadSampleButton").addEventListener("click", () => loadSample().catch((error) => showToast(error.message)));
document.getElementById("toggleConclusionButton").addEventListener("click", () => toggleConclusion().catch((error) => showToast(error.message)));
document.getElementById("markPassButton").addEventListener("click", () => markConclusion("通过").catch((error) => showToast(error.message)));
document.getElementById("markFailButton").addEventListener("click", () => markConclusion("失败").catch((error) => showToast(error.message)));
document.getElementById("clearConclusionButton").addEventListener("click", () => markConclusion("").catch((error) => showToast(error.message)));
document.getElementById("formatJsonButton").addEventListener("click", formatResponseJson);
document.getElementById("makeContainsButton").addEventListener("click", makeContainsCheck);

loadCases().catch((error) => showToast(error.message));
