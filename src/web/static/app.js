/* === State === */
const state = {
    step: 1,
    url: null,
    parsed: null,
    fileInfo: null,
    data: null,
    revisionId: null,
    selectedPath: null,
    selectedValue: null,
    selectedDesc: null,
    selectedPreview: null,
};

/* === DOM Refs === */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

/* === Step Navigation === */
function goToStep(n) {
    state.step = n;
    $$(".step-content").forEach((el) => {
        el.classList.remove("active");
        el.classList.add("hidden");
    });
    const target = $(`#step-${n}`);
    target.classList.remove("hidden");
    target.classList.add("active");

    $$(".steps .step").forEach((el) => {
        const s = parseInt(el.dataset.step);
        el.classList.remove("active", "completed");
        if (s === n) el.classList.add("active");
        else if (s < n) el.classList.add("completed");
    });
}

/* === API Helpers === */
async function api(endpoint, body) {
    const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
}

/* === Step 1: Fetch File === */
async function handleFetch() {
    const url = $("#url-input").value.trim();
    if (!url) return;

    $("#url-error").classList.add("hidden");
    $("#loading-fetch").classList.remove("hidden");
    $("#fetch-btn").disabled = true;

    try {
        const result = await api("/api/fetch-file", { url });
        state.url = url;
        state.parsed = result.parsed;
        state.fileInfo = result.file_info;
        state.data = result.data;
        state.revisionId = result.revision_id;

        renderFileInfo();
        renderTree();
        goToStep(2);
    } catch (err) {
        $("#url-error").textContent = err.message;
        $("#url-error").classList.remove("hidden");
    } finally {
        $("#loading-fetch").classList.add("hidden");
        $("#fetch-btn").disabled = false;
    }
}

/* === File Info Bar === */
function renderFileInfo() {
    const info = state.fileInfo;
    const name = info.display_name || info.name || "Unknown";
    let sizeStr = "";
    if (info.size > 1000000) sizeStr = (info.size / 1000000).toFixed(1) + " MB";
    else if (info.size > 1000) sizeStr = (info.size / 1000).toFixed(1) + " KB";
    else if (info.size) sizeStr = info.size + " bytes";

    $("#file-info-bar").innerHTML = `
        <div><div class="fi-label">File</div><div class="fi-value">${esc(name)}</div></div>
        ${sizeStr ? `<div><div class="fi-label">Size</div><div class="fi-value">${esc(sizeStr)}</div></div>` : ""}
        <div><div class="fi-label">Revisions</div><div class="fi-value">${info.revision_count || 0}</div></div>
    `;
}

/* === JSON Tree Renderer === */
function renderTree() {
    const container = $("#json-tree");
    container.innerHTML = "";
    const ul = buildTreeNode(state.data, "", 0);
    container.appendChild(ul);
}

function buildTreeNode(data, parentPath, depth) {
    const ul = document.createElement("ul");
    ul.className = "tree-node";

    if (data === null || data === undefined) return ul;

    const entries = Array.isArray(data)
        ? data.map((v, i) => [i, v])
        : Object.entries(data);

    for (const [key, value] of entries) {
        const isIndex = typeof key === "number";
        const path = parentPath
            ? (isIndex ? `${parentPath}[${key}]` : `${parentPath}.${key}`)
            : (isIndex ? `[${key}]` : String(key));

        const isExpandable = value !== null && typeof value === "object";
        const li = document.createElement("li");

        // Row
        const row = document.createElement("div");
        row.className = "tree-node-row";
        row.dataset.path = path;

        // Toggle arrow
        const toggle = document.createElement("span");
        toggle.className = isExpandable ? "tree-toggle" : "tree-toggle leaf";
        toggle.textContent = "\u25B6";
        row.appendChild(toggle);

        // Key or index label
        const keySpan = document.createElement("span");
        keySpan.className = isIndex ? "tree-index" : "tree-key";
        keySpan.textContent = isIndex ? `[${key}]` : `"${key}"`;
        row.appendChild(keySpan);

        // Colon
        const colon = document.createElement("span");
        colon.className = "tree-colon";
        colon.textContent = ":";
        row.appendChild(colon);

        // Type badge
        const badge = document.createElement("span");
        badge.className = "type-badge " + getTypeBadgeClass(value);
        badge.textContent = getTypeBadgeText(value);
        row.appendChild(badge);

        // Inline value preview for scalars
        if (!isExpandable) {
            const valSpan = document.createElement("span");
            valSpan.className = "tree-value-inline";
            valSpan.textContent = formatScalar(value);
            row.appendChild(valSpan);
        }

        li.appendChild(row);

        // Children (expandable)
        if (isExpandable) {
            const childUl = buildTreeNode(value, path, depth + 1);
            childUl.style.display = depth < 1 ? "block" : "none";
            if (depth < 1) toggle.classList.add("expanded");
            li.appendChild(childUl);

            // Toggle expand/collapse
            toggle.addEventListener("click", (e) => {
                e.stopPropagation();
                const isOpen = childUl.style.display !== "none";
                childUl.style.display = isOpen ? "none" : "block";
                toggle.classList.toggle("expanded", !isOpen);
            });
        }

        // Click to select
        row.addEventListener("click", () => selectNode(path, row));

        ul.appendChild(li);
    }

    return ul;
}

function getTypeBadgeClass(value) {
    if (value === null) return "type-null";
    if (Array.isArray(value)) return "type-array";
    switch (typeof value) {
        case "object": return "type-object";
        case "string": return "type-string";
        case "number": return "type-number";
        case "boolean": return "type-boolean";
        default: return "type-null";
    }
}

function getTypeBadgeText(value) {
    if (value === null) return "null";
    if (Array.isArray(value)) return `array(${value.length})`;
    switch (typeof value) {
        case "object": return `object(${Object.keys(value).length})`;
        case "string": return "string";
        case "number": return "number";
        case "boolean": return "boolean";
        default: return "null";
    }
}

function formatScalar(value) {
    if (value === null) return "null";
    if (typeof value === "string") {
        const s = value.length > 60 ? value.slice(0, 60) + "..." : value;
        return `"${s}"`;
    }
    return String(value);
}

/* === Node Selection === */
async function selectNode(path, rowEl) {
    // Highlight
    $$(".tree-node-row.selected").forEach((el) => el.classList.remove("selected"));
    rowEl.classList.add("selected");

    state.selectedPath = path;

    // Get preview from server (reuses Python resolve_path logic)
    try {
        const result = await api("/api/resolve-path", {
            data: state.data,
            path: path,
        });
        state.selectedValue = result.value;
        state.selectedDesc = result.description;
        state.selectedPreview = result.preview;

        // Update preview panel
        $("#selection-info").classList.remove("selection-placeholder");
        $("#selection-info").innerHTML = `
            <div style="font-size:13px">
                <strong>Path:</strong> <code>${esc(path)}</code><br>
                <strong>Type:</strong> ${esc(result.description)}
            </div>
        `;
        $("#selection-preview").textContent = result.preview;
        $("#selection-preview").classList.remove("hidden");
        $("#preview-actions").classList.remove("hidden");
    } catch (err) {
        $("#selection-info").innerHTML = `<div class="error-msg">${esc(err.message)}</div>`;
        $("#selection-preview").classList.add("hidden");
        $("#preview-actions").classList.add("hidden");
    }
}

/* === Step 3: Extract Preview === */
function handleExtract() {
    if (!state.selectedPath) return;

    const originalName = state.fileInfo.name || "file.json";
    const leafKey = state.selectedPath.includes(".")
        ? state.selectedPath.split(".").pop()
        : state.selectedPath;
    const safeName = originalName.replace(/\.[^.]+$/, "") + "_" + leafKey.replace(/[^\w\-.]/g, "_") + ".json";

    $("#extract-meta").innerHTML = `
        <span class="meta-label">Source file:</span><span class="meta-value">${esc(originalName)}</span>
        <span class="meta-label">Element path:</span><span class="meta-value">${esc(state.selectedPath)}</span>
        <span class="meta-label">Type:</span><span class="meta-value">${esc(state.selectedDesc)}</span>
        <span class="meta-label">New filename:</span><span class="meta-value">${esc(safeName)}</span>
        <span class="meta-label">Description:</span><span class="meta-value">Extracted '${esc(state.selectedPath)}' from ${esc(originalName)}</span>
    `;

    // Full preview (not truncated)
    const fullPreview = JSON.stringify(state.selectedValue, null, 2);
    const lines = fullPreview.split("\n");
    if (lines.length > 100) {
        $("#extract-preview").textContent = lines.slice(0, 100).join("\n") + `\n\n... (${lines.length - 100} more lines)`;
    } else {
        $("#extract-preview").textContent = fullPreview;
    }

    goToStep(3);
}

/* === Step 4: Upload === */
async function handleUpload() {
    goToStep(4);
    $("#loading-upload").classList.remove("hidden");
    $("#result-card").innerHTML = "";
    $("#result-actions").style.display = "none";

    try {
        const result = await api("/api/upload", {
            file_id: state.parsed.file_id,
            path: state.selectedPath,
            original_name: state.fileInfo.name || "file.json",
            host: state.parsed.host,
            model_id: state.fileInfo.model_id || null,
        });

        $("#result-card").className = "card result-card success";
        $("#result-card").innerHTML = `
            <h2>Upload Complete</h2>
            <p>The extracted element has been created as a new file in Istari with source traceability.</p>
            <div class="result-details">
                <span class="meta-label">New file:</span><span>${esc(result.filename)}</span>
                <span class="meta-label">File ID:</span><span><code>${esc(result.new_file_id)}</code></span>
                <span class="meta-label">Source revision:</span><span><code>${esc(result.revision_id)}</code></span>
                <span class="meta-label">URL:</span><span><a href="${esc(result.url)}" target="_blank">${esc(result.url)}</a></span>
            </div>
        `;
    } catch (err) {
        $("#result-card").className = "card result-card error";
        $("#result-card").innerHTML = `
            <h2>Upload Failed</h2>
            <p>${esc(err.message)}</p>
        `;
    } finally {
        $("#loading-upload").classList.add("hidden");
        $("#result-actions").style.display = "flex";
    }
}

/* === Expand / Collapse All === */
function expandAll() {
    $$("#json-tree ul").forEach((ul) => (ul.style.display = "block"));
    $$("#json-tree .tree-toggle").forEach((t) => {
        if (!t.classList.contains("leaf")) t.classList.add("expanded");
    });
}
function collapseAll() {
    $$("#json-tree .tree-node > li > ul").forEach((ul) => (ul.style.display = "none"));
    // Keep top-level visible
    const topUl = $("#json-tree > ul");
    if (topUl) topUl.style.display = "block";
    $$("#json-tree .tree-toggle").forEach((t) => t.classList.remove("expanded"));
}

/* === Restart === */
function restart() {
    state.step = 1;
    state.url = null;
    state.parsed = null;
    state.fileInfo = null;
    state.data = null;
    state.revisionId = null;
    state.selectedPath = null;
    state.selectedValue = null;
    state.selectedDesc = null;
    state.selectedPreview = null;

    $("#url-input").value = "";
    $("#url-error").classList.add("hidden");
    $("#selection-info").className = "selection-placeholder";
    $("#selection-info").textContent = "Click a node in the tree to select it for extraction";
    $("#selection-preview").classList.add("hidden");
    $("#preview-actions").classList.add("hidden");

    goToStep(1);
}

/* === Escape HTML === */
function esc(str) {
    const div = document.createElement("div");
    div.textContent = String(str);
    return div.innerHTML;
}

/* === Event Bindings === */
document.addEventListener("DOMContentLoaded", () => {
    // Step 1
    $("#fetch-btn").addEventListener("click", handleFetch);
    $("#url-input").addEventListener("keydown", (e) => {
        if (e.key === "Enter") handleFetch();
    });

    // Step 2
    $("#extract-btn").addEventListener("click", handleExtract);
    $("#expand-all-btn").addEventListener("click", expandAll);
    $("#collapse-all-btn").addEventListener("click", collapseAll);
    $("#back-to-1").addEventListener("click", () => goToStep(1));

    // Step 3
    $("#back-to-2").addEventListener("click", () => goToStep(2));
    $("#confirm-upload-btn").addEventListener("click", handleUpload);

    // Step 4
    $("#restart-btn").addEventListener("click", restart);
});
