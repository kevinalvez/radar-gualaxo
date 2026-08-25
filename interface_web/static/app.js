// ---------- Tabs ----------

const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanels = document.querySelectorAll(".tab-panel");

tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
        tabButtons.forEach((b) => b.classList.remove("active"));
        tabPanels.forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    });
});

// ---------- Toast ----------

const toastEl = document.getElementById("toast");
let toastTimer = null;

function showToast(message, kind = "info") {
    toastEl.textContent = message;
    toastEl.className = "toast" + (kind === "error" ? " toast-error" : kind === "success" ? " toast-success" : "");
    toastEl.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toastEl.hidden = true; }, 3500);
}

// ---------- Select all / none ----------

document.querySelectorAll("[data-select]").forEach((btn) => {
    btn.addEventListener("click", () => {
        const name = btn.dataset.select;
        const checked = btn.dataset.mode === "all";
        document.querySelectorAll(`input[name="${name}"]`).forEach((input) => {
            input.checked = checked;
            input.dispatchEvent(new Event("change"));
        });
    });
});

// Keep chip visual state (border/background) in sync even on browsers
// without :has() support.
document.querySelectorAll(".chip input").forEach((input) => {
    const sync = () => input.closest(".chip").classList.toggle("checked", input.checked);
    input.addEventListener("change", sync);
    sync();
});

// ---------- Source table wiring (search filter, row click-to-toggle,
// header "select all") - reused for both the Busca tab's #source-table
// and the Orquestração tab's #orch-source-table, which are otherwise
// independent selections (different `name` on their checkboxes). ----------

function wireSourceTable(tableId, searchInputId, selectAllId, inputName) {
    const search = document.getElementById(searchInputId);
    if (search) {
        search.addEventListener("input", () => {
            const query = search.value.trim().toLowerCase();
            document.querySelectorAll(`#${tableId} .source-row`).forEach((row) => {
                const matches = !query || row.dataset.name.includes(query);
                row.classList.toggle("filtered-out", !matches);
            });
        });
    }

    document.querySelectorAll(`#${tableId} .source-row`).forEach((row) => {
        row.addEventListener("click", (event) => {
            if (event.target.tagName === "INPUT") return;
            const input = row.querySelector('input[type="checkbox"]');
            input.checked = !input.checked;
            input.dispatchEvent(new Event("change"));
        });
    });

    const selectAll = document.getElementById(selectAllId);
    if (!selectAll) return;

    const inputs = () => document.querySelectorAll(`#${tableId} input[name="${inputName}"]`);

    const syncSelectAll = () => {
        const all = inputs();
        const checked = document.querySelectorAll(`#${tableId} input[name="${inputName}"]:checked`);
        selectAll.checked = all.length > 0 && all.length === checked.length;
    };

    selectAll.addEventListener("change", () => {
        inputs().forEach((input) => { input.checked = selectAll.checked; });
    });

    inputs().forEach((input) => input.addEventListener("change", syncSelectAll));

    syncSelectAll();
}

wireSourceTable("source-table", "source-search", "source-select-all", "source");
wireSourceTable("orch-source-table", "orch-source-search", "orch-source-select-all", "orch_source");

// ---------- Run + poll ----------

const runBtn = document.getElementById("run-btn");
const progressWrap = document.getElementById("progress-wrap");
const progressFill = document.getElementById("progress-fill");
const progressText = document.getElementById("progress-text");
const progressStatus = document.getElementById("progress-status");
const logEl = document.getElementById("log");
const resultsBadge = document.getElementById("results-badge");

let pollTimer = null;
let lastResults = [];

function selectedValues(name) {
    return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map((el) => el.value);
}

// <input type="date"> gives "YYYY-MM-DD" - the backend (matching
// Pipeline.filter_by_date) expects "DD/MM/YYYY".
function isoToBr(isoDate) {
    if (!isoDate) return "";
    const [year, month, day] = isoDate.split("-");
    return `${day}/${month}/${year}`;
}

// ---------- Busca: custom period fields ----------

const periodCustomFields = document.getElementById("period-custom-fields");
document.querySelectorAll('input[name="period"]').forEach((input) => {
    input.addEventListener("change", () => {
        periodCustomFields.hidden = input.value !== "custom" || !input.checked;
    });
});

runBtn.addEventListener("click", async () => {
    const keywords = selectedValues("keyword");
    const sources = selectedValues("source");
    const period = document.querySelector('input[name="period"]:checked').value;

    if (keywords.length === 0) {
        showToast("Selecione ao menos uma palavra-chave.", "error");
        return;
    }
    if (sources.length === 0) {
        showToast("Selecione ao menos uma fonte.", "error");
        return;
    }

    const runPayload = { keywords, sources, period };

    if (period === "custom") {
        runPayload.start_date = isoToBr(document.getElementById("period-start").value);
        runPayload.end_date = isoToBr(document.getElementById("period-end").value);

        if (!runPayload.start_date || !runPayload.end_date) {
            showToast("Informe a data inicial e final do período específico.", "error");
            return;
        }
    }

    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="btn-icon">⏳</span> Rodando...';
    progressWrap.hidden = false;
    logEl.textContent = "";
    progressFill.style.width = "0%";
    progressText.textContent = "iniciando...";
    setStatusPill("running");

    // A new run invalidates whatever the previous one showed - clear
    // Resultados/Clipping immediately (not just when this run finishes)
    // so nothing stale from the last run/keyword-selection is left on
    // screen while this one is still in progress.
    clearInterval(pollTimer);
    lastResults = [];
    renderResults(lastResults);
    resetClippingPreview();

    const response = await fetch("/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(runPayload),
    });

    if (!response.ok) {
        const data = await response.json();
        showToast(data.error || "Erro ao iniciar.", "error");
        resetRunButton();
        return;
    }

    pollTimer = setInterval(pollStatus, 1000);
});

function setStatusPill(state) {
    progressStatus.className = "status-pill status-" + state;
    progressStatus.textContent = { running: "executando", done: "concluído", error: "erro" }[state] || state;
}

function resetRunButton() {
    runBtn.disabled = false;
    runBtn.innerHTML = '<span class="btn-icon">▶</span> Rodar monitoramento';
}

async function pollStatus() {
    const response = await fetch("/status");
    const job = await response.json();

    if (job.status === "idle") return;

    const { done, total } = job.progress || { done: 0, total: 0 };
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;
    progressFill.style.width = pct + "%";
    progressText.textContent = `${done} / ${total} fontes`;
    logEl.textContent = (job.log || []).join("\n");
    logEl.scrollTop = logEl.scrollHeight;

    if (job.status === "done" || job.status === "error") {
        clearInterval(pollTimer);
        resetRunButton();
        setStatusPill(job.status);

        if (job.status === "done") {
            lastResults = job.results || [];
            renderResults(lastResults);
            showToast(`${lastResults.length} publicações encontradas.`, "success");
        } else {
            showToast("A execução falhou - veja o log.", "error");
        }
    }
}

// ---------- Results table ----------

const resultsEmpty = document.getElementById("results-empty");
const resultsTableWrap = document.getElementById("results-table-wrap");
const resultsBody = document.querySelector("#results-table tbody");
const resultsSearch = document.getElementById("results-search");
const exportExcelBtn = document.getElementById("export-excel-btn");

exportExcelBtn.addEventListener("click", () => {
    window.location.href = "/results/export.xlsx";
});

let sortKey = null;
let sortAsc = true;

function renderResults(results) {
    resultsBadge.hidden = results.length === 0;
    resultsBadge.textContent = results.length;
    exportExcelBtn.disabled = results.length === 0;

    if (results.length === 0) {
        resultsEmpty.hidden = false;
        resultsTableWrap.hidden = true;
        return;
    }

    resultsEmpty.hidden = true;
    resultsTableWrap.hidden = false;
    paintResultsRows(results);
}

function paintResultsRows(results) {
    const query = resultsSearch.value.trim().toLowerCase();
    let rows = results.filter((item) => {
        if (!query) return true;
        return (
            item.title.toLowerCase().includes(query) ||
            item.source.toLowerCase().includes(query) ||
            (item.category || "").toLowerCase().includes(query)
        );
    });

    if (sortKey) {
        rows = [...rows].sort((a, b) => {
            const av = (a[sortKey] || "").toString().toLowerCase();
            const bv = (b[sortKey] || "").toString().toLowerCase();
            return av < bv ? (sortAsc ? -1 : 1) : av > bv ? (sortAsc ? 1 : -1) : 0;
        });
    }

    resultsBody.innerHTML = "";
    for (const item of rows) {
        const row = document.createElement("tr");

        const titleCell = document.createElement("td");
        const link = document.createElement("a");
        link.href = item.url;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = item.title;
        titleCell.appendChild(link);

        const sourceCell = document.createElement("td");
        sourceCell.textContent = item.source;

        const categoryCell = document.createElement("td");
        categoryCell.className = "category-tag";
        categoryCell.textContent = item.category || "";

        const dateCell = document.createElement("td");
        dateCell.textContent = item.date || "—";

        const keywordsCell = document.createElement("td");
        for (const kw of item.keywords) {
            const tag = document.createElement("span");
            tag.className = "keyword-tag";
            tag.textContent = kw;
            keywordsCell.appendChild(tag);
        }

        const summaryCell = document.createElement("td");
        summaryCell.className = "summary-cell";
        summaryCell.textContent = item.summary || "—";

        row.append(titleCell, sourceCell, categoryCell, dateCell, keywordsCell, summaryCell);
        resultsBody.appendChild(row);
    }
}

resultsSearch.addEventListener("input", () => paintResultsRows(lastResults));

document.querySelectorAll("#results-table th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
        const key = th.dataset.sort;
        sortAsc = sortKey === key ? !sortAsc : true;
        sortKey = key;
        paintResultsRows(lastResults);
    });
});

// ---------- Clipping ----------

const generateClippingBtn = document.getElementById("generate-clipping-btn");
const copyClippingBtn = document.getElementById("copy-clipping-btn");
const downloadClippingBtn = document.getElementById("download-clipping-btn");
const sendWhatsappBtn = document.getElementById("send-whatsapp-btn");
const clippingEmpty = document.getElementById("clipping-empty");
const clippingPreview = document.getElementById("clipping-preview");

function resetClippingPreview() {
    clippingEmpty.hidden = false;
    clippingPreview.hidden = true;
    clippingPreview.textContent = "";
    copyClippingBtn.disabled = true;
    downloadClippingBtn.disabled = true;
    sendWhatsappBtn.disabled = true;
}

generateClippingBtn.addEventListener("click", async () => {
    const response = await fetch("/clipping");
    const data = await response.json();

    if (!response.ok) {
        showToast(data.error || "Erro ao gerar clipping.", "error");
        return;
    }

    clippingEmpty.hidden = true;
    clippingPreview.hidden = false;
    clippingPreview.textContent = data.text;
    copyClippingBtn.disabled = false;
    downloadClippingBtn.disabled = false;
    sendWhatsappBtn.disabled = false;
});

copyClippingBtn.addEventListener("click", async () => {
    await navigator.clipboard.writeText(clippingPreview.textContent);
    showToast("Clipping copiado para a área de transferência.", "success");
});

downloadClippingBtn.addEventListener("click", () => {
    const blob = new Blob([clippingPreview.textContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `clipping-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
});

sendWhatsappBtn.addEventListener("click", async () => {
    const confirmed = confirm(
        "Isso vai abrir o Chrome nesta máquina e enviar esse clipping de verdade pro grupo do WhatsApp configurado. Confirma o envio?"
    );
    if (!confirmed) return;

    sendWhatsappBtn.disabled = true;
    sendWhatsappBtn.textContent = "Enviando...";

    const response = await fetch("/whatsapp/send", { method: "POST" });
    const data = await response.json();

    if (!response.ok) {
        showToast(data.error || "Erro ao iniciar o envio.", "error");
    } else {
        showToast("Envio iniciado - acompanhe a janela do Chrome nesta máquina.", "success");
    }

    sendWhatsappBtn.disabled = false;
    sendWhatsappBtn.textContent = "📲 Enviar pro WhatsApp";
});

// ---------- Configuração: keywords ----------

async function postJson(url, body) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await response.json();
    return { ok: response.ok, data };
}

document.querySelectorAll(".keyword-remove-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
        const li = btn.closest("li");
        const { ok, data } = await postJson("/keywords/remove", { value: li.dataset.value });
        if (!ok) {
            showToast(data.error || "Erro ao remover.", "error");
            return;
        }
        window.location.reload();
    });
});

const keywordAddForm = document.getElementById("keyword-add-form");
keywordAddForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const input = document.getElementById("keyword-add-input");
    const { ok, data } = await postJson("/keywords/add", { value: input.value });
    if (!ok) {
        showToast(data.error || "Erro ao adicionar.", "error");
        return;
    }
    window.location.reload();
});

// ---------- Orquestração ----------

const orchIntervalFields = document.getElementById("orch-interval-fields");
const orchWeekdayFields = document.getElementById("orch-weekday-fields");

function syncOrchestrationMode() {
    const mode = document.querySelector('input[name="orch-mode"]:checked').value;
    orchIntervalFields.hidden = mode !== "interval";
    orchWeekdayFields.hidden = mode !== "weekdays";
}

document.querySelectorAll('input[name="orch-mode"]').forEach((input) => {
    input.addEventListener("change", syncOrchestrationMode);
});
syncOrchestrationMode();

// Dropdown: toggle open/closed, close on outside click, keep the
// button's label in sync with what's actually checked.
const orchWeekdayToggle = document.getElementById("orch-weekday-toggle");
const orchWeekdayPanel = document.getElementById("orch-weekday-panel");
const orchWeekdayLabel = document.getElementById("orch-weekday-label");
const WEEKDAY_SHORT_LABELS = { mon: "Seg", tue: "Ter", wed: "Qua", thu: "Qui", fri: "Sex", sat: "Sáb", sun: "Dom" };

orchWeekdayToggle.addEventListener("click", (event) => {
    event.stopPropagation();
    orchWeekdayPanel.hidden = !orchWeekdayPanel.hidden;
});

document.addEventListener("click", (event) => {
    if (!orchWeekdayPanel.hidden && !orchWeekdayPanel.contains(event.target) && event.target !== orchWeekdayToggle) {
        orchWeekdayPanel.hidden = true;
    }
});

function syncWeekdayLabel() {
    const selected = selectedValues("orch_weekday");
    orchWeekdayLabel.textContent = selected.length > 0
        ? selected.map((code) => WEEKDAY_SHORT_LABELS[code] || code).join(", ")
        : "Selecione os dias";
}

document.querySelectorAll('input[name="orch_weekday"]').forEach((input) => {
    input.addEventListener("change", syncWeekdayLabel);
});
syncWeekdayLabel();

const orchPeriodCustomFields = document.getElementById("orch-period-custom-fields");
document.querySelectorAll('input[name="orch-period"]').forEach((input) => {
    input.addEventListener("change", () => {
        orchPeriodCustomFields.hidden = input.value !== "custom" || !input.checked;
    });
});

const orchestrationForm = document.getElementById("orchestration-form");
orchestrationForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const mode = document.querySelector('input[name="orch-mode"]:checked').value;
    const time = document.getElementById("orch-time").value;
    const period = document.querySelector('input[name="orch-period"]:checked').value;
    const keywords = selectedValues("orch_keyword");
    const sources = selectedValues("orch_source");

    const payload = { mode, time, period, keywords, sources };

    if (mode === "weekdays") {
        payload.weekdays = selectedValues("orch_weekday");
        if (payload.weekdays.length === 0) {
            showToast("Selecione ao menos um dia da semana.", "error");
            return;
        }
    } else {
        payload.interval_days = document.getElementById("orch-days").value;
    }

    if (period === "custom") {
        payload.start_date = isoToBr(document.getElementById("orch-period-start").value);
        payload.end_date = isoToBr(document.getElementById("orch-period-end").value);

        if (!payload.start_date || !payload.end_date) {
            showToast("Informe a data inicial e final do período específico.", "error");
            return;
        }
    }

    const { ok, data } = await postJson("/orchestration/save", payload);

    if (!ok) {
        showToast(data.error || "Erro ao salvar orquestração.", "error");
        return;
    }
    showToast("Orquestração salva.", "success");
    loadOrchestrationStatus();
});

async function loadOrchestrationStatus() {
    const response = await fetch("/orchestration/status");
    const data = await response.json();

    const nextEl = document.getElementById("orch-next-run");
    const lastEl = document.getElementById("orch-last-run");

    nextEl.textContent = data.next_run_at || "não agendado";

    if (data.last_run_error) {
        lastEl.textContent = `${data.last_run_at || "—"} (erro: ${data.last_run_error})`;
    } else if (data.last_run_at) {
        lastEl.textContent = `${data.last_run_at} (${data.last_run_count} publicações)`;
    } else {
        lastEl.textContent = "ainda não rodou";
    }
}

loadOrchestrationStatus();

// ---------- Configuração: fontes ----------

const showAddSourceBtn = document.getElementById("show-add-source-btn");
const sourceAddForm = document.getElementById("source-add-form");
showAddSourceBtn.addEventListener("click", () => {
    sourceAddForm.hidden = !sourceAddForm.hidden;
});

const sourceCategorySelect = document.getElementById("source-category");
const sourceCategoryNew = document.getElementById("source-category-new");
sourceCategorySelect.addEventListener("change", () => {
    sourceCategoryNew.hidden = sourceCategorySelect.value !== "__new__";
    if (!sourceCategoryNew.hidden) sourceCategoryNew.focus();
});

sourceAddForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const category = sourceCategorySelect.value === "__new__"
        ? sourceCategoryNew.value.trim()
        : sourceCategorySelect.value;

    const { ok, data } = await postJson("/sources/add", {
        name: document.getElementById("source-name").value,
        provider: document.getElementById("source-provider").value,
        category: category,
        url: document.getElementById("source-url").value,
        description: document.getElementById("source-description").value,
        enabled: document.getElementById("source-enabled").checked,
    });

    if (!ok) {
        showToast(data.error || "Erro ao salvar fonte.", "error");
        return;
    }
    window.location.reload();
});

document.querySelectorAll(".source-toggle").forEach((toggle) => {
    toggle.addEventListener("change", async () => {
        const name = toggle.closest("tr").dataset.name;
        const { ok, data } = await postJson("/sources/toggle", { name });
        if (!ok) {
            showToast(data.error || "Erro ao atualizar fonte.", "error");
            toggle.checked = !toggle.checked;
            return;
        }
        showToast(`${name}: ${data.enabled ? "ativada" : "desativada"}.`, "success");
    });
});

document.querySelectorAll(".source-remove-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
        const row = btn.closest("tr");
        const name = row.dataset.name;
        if (!confirm(`Excluir a fonte "${name}"?`)) return;

        const { ok, data } = await postJson("/sources/remove", { name });
        if (!ok) {
            showToast(data.error || "Erro ao excluir fonte.", "error");
            return;
        }
        window.location.reload();
    });
});
