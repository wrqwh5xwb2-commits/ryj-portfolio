const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
let result = null,
  image = null,
  activeId = null,
  busy = false;
const canvas = $("#canvas"),
  ctx = canvas.getContext("2d");
function status(message) {
  $("#status").textContent = message;
}
function threshold() {
  const value = Number($("#threshold").value);
  return Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0.97;
}
function setBusy(value) {
  busy = value;
  $("#file").disabled = value;
  $$("[data-sample]").forEach((button) => (button.disabled = value));
  $$("[data-export],#mark-all").forEach(
    (button) => (button.disabled = value || !result?.lines.length),
  );
}
function draw() {
  if (!image) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, 0, 0);
  result.lines.forEach((line) => {
    ctx.beginPath();
    line.box.forEach((p, i) => (i ? ctx.lineTo(...p) : ctx.moveTo(...p)));
    ctx.closePath();
    ctx.strokeStyle = line.score < threshold() ? "#bf8736" : "#299b71";
    ctx.lineWidth = line.id === activeId ? 5 : 2;
    ctx.stroke();
    if (line.id === activeId) {
      ctx.fillStyle = "#17634922";
      ctx.fill();
    }
  });
}
function counts() {
  const lines = result?.lines || [];
  $("#count").textContent = `${lines.length} 行`;
  $("#review-count").textContent =
    `已核对 ${lines.filter((x) => x.reviewed).length} / ${lines.length} · 已修改 ${lines.filter((x) => x.text !== x.original).length}`;
}
function renderRows() {
  $("#rows").replaceChildren();
  const visible = (result?.lines || []).filter(
    (x) => !$("#only-low").checked || x.score < threshold(),
  );
  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = result?.lines.length
      ? "当前没有低于阈值的行。"
      : "未检测到文字，可换一张清晰图片。";
    $("#rows").append(empty);
  }
  visible.forEach((line) => {
    const row = document.createElement("div");
    row.className = `row${line.score < threshold() ? " low" : ""}${line.id === activeId ? " active" : ""}`;
    row.dataset.id = line.id;
    const top = document.createElement("div");
    top.className = "row-top";
    const label = document.createElement("label");
    label.className = "check";
    const check = document.createElement("input");
    check.type = "checkbox";
    check.checked = !!line.reviewed;
    check.setAttribute("aria-label", `第${line.id}行已核对`);
    check.addEventListener("change", () => {
      line.reviewed = check.checked;
      counts();
    });
    label.append(check, document.createTextNode(`第 ${line.id} 行 · 已核对`));
    const score = document.createElement("span");
    score.className = "score";
    score.textContent = line.score.toFixed(3);
    top.append(label, score);
    const input = document.createElement("input");
    input.type = "text";
    input.value = line.text;
    input.maxLength = 10000;
    input.setAttribute("aria-label", `第${line.id}行文字`);
    input.addEventListener("focus", () => {
      activeId = line.id;
      $$(".row").forEach((r) =>
        r.classList.toggle("active", Number(r.dataset.id) === activeId),
      );
      draw();
    });
    input.addEventListener("input", () => {
      line.text = input.value;
      line.reviewed = false;
      check.checked = false;
      counts();
    });
    const original = document.createElement("p");
    original.className = "original";
    original.textContent = `原始识别：${line.original}`;
    row.append(top, input, original);
    $("#rows").append(row);
  });
  counts();
  draw();
}
async function recognize(file) {
  if (busy) return;
  if (file.size > 8 * 1024 * 1024) return status("图片超过8MB，请先缩小。");
  result = null;
  image = null;
  activeId = null;
  $("#rows").replaceChildren();
  $("#canvas").hidden = true;
  $("#placeholder").hidden = false;
  $("#dimensions").textContent = "处理中";
  counts();
  setBusy(true);
  status("正在本机识别文字，首次运行需要加载模型…");
  const controller = new AbortController(),
    timeout = setTimeout(() => controller.abort(), 90000);
  try {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch("/api/recognize", {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok)
      throw Error(
        typeof data.detail === "string" ? data.detail : "图片处理失败",
      );
    const preview = new Image();
    await new Promise((resolve, reject) => {
      preview.onload = resolve;
      preview.onerror = () => reject(Error("预览加载失败"));
      preview.src = data.preview;
    });
    result = data;
    image = preview;
    canvas.width = preview.naturalWidth;
    canvas.height = preview.naturalHeight;
    $("#canvas").hidden = false;
    $("#placeholder").hidden = true;
    $("#dimensions").textContent = data.working_size.join(" × ");
    renderRows();
    status(
      data.lines.length
        ? `识别到 ${data.lines.length} 行 · 推理 ${data.elapsed_ms} ms（不含模型加载）。请对照原图校对。`
        : "未检测到文字。空白、失焦或过小的文字都可能导致这个结果。",
    );
  } catch (error) {
    status(
      error.name === "AbortError"
        ? "识别超时，请缩小图片重试。"
        : error.message,
    );
    $("#dimensions").textContent = "处理失败";
  } finally {
    clearTimeout(timeout);
    setBusy(false);
  }
}
$("#file").addEventListener("change", (e) => {
  if (e.target.files[0]) recognize(e.target.files[0]);
  e.target.value = "";
});
$$("[data-sample]").forEach((button) =>
  button.addEventListener("click", async () => {
    if (busy) return;
    setBusy(true);
    try {
      const response = await fetch(`/samples/${button.dataset.sample}.png`);
      if (!response.ok) throw Error("示例加载失败");
      const blob = await response.blob();
      setBusy(false);
      await recognize(
        new File([blob], `${button.dataset.sample}.png`, { type: "image/png" }),
      );
    } catch (error) {
      status(error.message);
      setBusy(false);
    }
  }),
);
$("#threshold").addEventListener("change", () => {
  $("#threshold").value = threshold();
  renderRows();
});
$("#only-low").addEventListener("change", renderRows);
$("#mark-all").addEventListener("click", () => {
  result.lines.forEach((x) => (x.reviewed = true));
  renderRows();
});
canvas.addEventListener("click", (e) => {
  if (!result) return;
  const box = canvas.getBoundingClientRect(),
    x = ((e.clientX - box.left) / box.width) * canvas.width,
    y = ((e.clientY - box.top) / box.height) * canvas.height;
  const line = result.lines.find(
    (r) =>
      x >= Math.min(...r.box.map((p) => p[0])) &&
      x <= Math.max(...r.box.map((p) => p[0])) &&
      y >= Math.min(...r.box.map((p) => p[1])) &&
      y <= Math.max(...r.box.map((p) => p[1])),
  );
  if (line) {
    activeId = line.id;
    $("#only-low").checked = false;
    renderRows();
    const row = $(`.row[data-id="${line.id}"]`);
    row?.scrollIntoView({ block: "nearest" });
    row?.querySelector("input[type=text]").focus({ preventScroll: true });
  }
});
function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
$$("[data-export]").forEach((button) =>
  button.addEventListener("click", async () => {
    if (busy || !result?.lines.length) return;
    const kind = button.dataset.export;
    if (kind === "txt")
      return download(
        new Blob([result.lines.map((x) => x.text).join("\n")], {
          type: "text/plain;charset=utf-8",
        }),
        "ocrdesk.txt",
      );
    if (kind === "json") {
      const { preview, ...data } = result;
      data.review_threshold = threshold();
      return download(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
        "ocrdesk-reviewed.json",
      );
    }
    try {
      const response = await fetch("/api/export/csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rows: result.lines }),
      });
      if (!response.ok) throw Error("CSV导出失败");
      download(await response.blob(), "ocrdesk-reviewed.csv");
    } catch (error) {
      status(error.message);
    }
  }),
);
fetch("/api/benchmark")
  .then((r) => r.json())
  .then((data) => {
    $("#benchmark").textContent = data
      ? `字符错误率 CER：${(data.character_error_rate * 100).toFixed(2)}% · ${data.cases.length} 张测试图片 · ${data.engine}`
      : "运行 check.cmd 后可查看报告。";
  })
  .catch(() => ($("#benchmark").textContent = "评测报告暂不可用"));
