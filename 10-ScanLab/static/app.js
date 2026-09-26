const $ = (s) => document.querySelector(s),
  $$ = (s) => [...document.querySelectorAll(s)];
let file = null,
  result = null,
  sourceImage = null,
  corners = [],
  selectedMode = "color",
  dirty = false,
  busy = false,
  dragIndex = -1,
  timer;
const canvas = $("#canvas"),
  ctx = canvas.getContext("2d");
function toast(t) {
  $("#toast").textContent = t;
  $("#toast").hidden = false;
  clearTimeout(timer);
  timer = setTimeout(() => ($("#toast").hidden = true), 6000);
}
function setBusy(value) {
  busy = value;
  $$(".action").forEach(
    (b) => (b.disabled = value || (!file && !b.dataset.sample)),
  );
  $("#file").disabled = value;
  $$("#aspect,#block,#offset,#coordinates input").forEach(
    (e) => (e.disabled = value),
  );
  $("#apply").textContent = value ? "正在处理…" : "应用四角与参数";
  showOutput();
}
function markDirty() {
  dirty = true;
  $("#download").disabled = true;
  $("#metadata").disabled = true;
  $("#status").textContent =
    "四角或参数已修改。点击「应用四角与参数」更新结果。";
  $("#status").classList.remove("warning");
}
function draw() {
  if (!sourceImage) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(sourceImage, 0, 0);
  if (corners.length !== 4) return;
  const ps = corners.map((p) => [
    p[0] * (canvas.width - 1),
    p[1] * (canvas.height - 1),
  ]);
  ctx.beginPath();
  ps.forEach((p, i) => (i ? ctx.lineTo(...p) : ctx.moveTo(...p)));
  ctx.closePath();
  ctx.fillStyle = "#235bc422";
  ctx.fill();
  ctx.strokeStyle = "#3685ff";
  ctx.lineWidth = Math.max(3, canvas.width / 250);
  ctx.stroke();
  ps.forEach((p, i) => {
    ctx.beginPath();
    ctx.arc(...p, canvas.width / 50, 0, Math.PI * 2);
    ctx.fillStyle = "#2364d5";
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = "white";
    ctx.stroke();
    ctx.fillStyle = "white";
    ctx.font = `bold ${canvas.width / 45}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(i + 1), ...p);
  });
}
function renderCoordinates() {
  const names = ["左上", "右上", "右下", "左下"];
  $("#coordinates").replaceChildren();
  corners.forEach((p, i) => {
    const row = document.createElement("div");
    row.className = "coordinate-row";
    const label = document.createElement("span");
    label.textContent = `${i + 1} ${names[i]}`;
    row.append(label);
    p.forEach((v, axis) => {
      const wrap = document.createElement("label");
      wrap.textContent = axis ? "Y" : "X";
      const input = document.createElement("input");
      input.type = "number";
      input.min = "0";
      input.max = "100";
      input.step = ".1";
      input.value = (v * 100).toFixed(1);
      input.setAttribute("aria-label", `${names[i]}${axis ? "Y" : "X"}百分比`);
      input.addEventListener("change", () => {
        const n = Number(input.value);
        if (!Number.isFinite(n) || n < 0 || n > 100)
          return toast("坐标需要在0至100之间");
        corners[i][axis] = n / 100;
        markDirty();
        draw();
      });
      wrap.append(input);
      row.append(wrap);
    });
    $("#coordinates").append(row);
  });
}
function point(e) {
  const r = canvas.getBoundingClientRect();
  return [
    Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)),
    Math.max(0, Math.min(1, (e.clientY - r.top) / r.height)),
  ];
}
canvas.addEventListener("pointerdown", (e) => {
  if (busy || !sourceImage) return;
  const p = point(e);
  let distance = 0.09;
  dragIndex = -1;
  corners.forEach((q, i) => {
    const d = Math.hypot(q[0] - p[0], q[1] - p[1]);
    if (d < distance) {
      distance = d;
      dragIndex = i;
    }
  });
  if (dragIndex >= 0) {
    canvas.setPointerCapture(e.pointerId);
    e.preventDefault();
  }
});
canvas.addEventListener("pointermove", (e) => {
  if (dragIndex < 0 || busy) return;
  corners[dragIndex] = point(e);
  markDirty();
  draw();
});
function endDrag() {
  if (dragIndex >= 0) renderCoordinates();
  dragIndex = -1;
}
canvas.addEventListener("pointerup", endDrag);
canvas.addEventListener("pointercancel", endDrag);
function showOutput() {
  const url = result?.outputs?.[selectedMode];
  $("#result").hidden = !url;
  $("#result-empty").hidden = !!url;
  if (url) $("#result").src = url;
  $("#download").disabled = !url || dirty || busy;
  $("#metadata").disabled = !url || dirty || busy;
  $$("[data-mode]").forEach((b) =>
    b.classList.toggle("selected", b.dataset.mode === selectedMode),
  );
}
async function processImage(manual = false) {
  if (!file || busy) return;
  setBusy(true);
  $("#status").textContent = "正在提取轮廓、计算透视变换并编码结果…";
  $("#download").disabled = true;
  $("#metadata").disabled = true;
  const form = new FormData();
  form.append("file", file);
  form.append("aspect", $("#aspect").value);
  form.append("block_size", $("#block").value);
  form.append("c", $("#offset").value);
  if (manual) form.append("corners", JSON.stringify(corners));
  const controller = new AbortController(),
    timeout = setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch("/api/process", {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok)
      throw Error(
        typeof data.detail === "string" ? data.detail : "参数无效，请检查输入",
      );
    const image = new Image();
    await new Promise((resolve, reject) => {
      image.onload = resolve;
      image.onerror = () => reject(Error("图片预览加载失败"));
      image.src = data.source;
    });
    result = data;
    sourceImage = image;
    corners = data.corners;
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    canvas.classList.add("loaded");
    $("#source-empty").hidden = true;
    dirty = false;
    draw();
    renderCoordinates();
    showOutput();
    $("#source-size").textContent = data.working_size.join(" × ");
    $("#result-size").textContent = data.output_size
      ? data.output_size.join(" × ")
      : "需要手动定位";
    $("#method").textContent =
      data.status === "needs_manual"
        ? "待手动确认"
        : data.method === "manual"
          ? "手动四角"
          : "自动检测";
    $("#candidates").textContent = data.candidate_count;
    $("#coverage").textContent = data.area_ratio
      ? `${Math.round(data.area_ratio * 100)}%`
      : "—";
    $("#latency").textContent = `${data.elapsed_ms} ms`;
    $("#edges").src = data.edges;
    $("#edges").hidden = false;
    $("#status").textContent = data.warnings.length
      ? data.warnings.join(" ")
      : "校正完成。请检查四角与文字细节；可以切换效果或下载结果。";
    $("#status").classList.toggle("warning", data.warnings.length > 0);
    if (data.status === "needs_manual") {
      $("#corner-hint").textContent =
        "当前四角只是起点，请手动贴合纸张边缘后应用。";
    } else {
      $("#corner-hint").textContent = "拖动蓝色圆点调整；角点不能交叉。";
    }
  } catch (e) {
    dirty = true;
    $("#status").textContent =
      "本次处理未成功，当前预览可能是上一版。请修正输入后重试。";
    $("#status").classList.add("warning");
    toast(e.name === "AbortError" ? "处理超时，请缩小图片后重试" : e.message);
  } finally {
    clearTimeout(timeout);
    setBusy(false);
  }
}
async function loadFile(next) {
  if (next.size > 12 * 1024 * 1024) return toast("图片不能超过12MB");
  file = next;
  result = null;
  sourceImage = null;
  corners = [];
  dirty = true;
  $("#source-empty").hidden = false;
  canvas.classList.remove("loaded");
  $("#source-size").textContent = "等待处理";
  $("#result-size").textContent = "等待处理";
  $("#edges").hidden = true;
  $("#coordinates").replaceChildren();
  showOutput();
  await processImage(false);
}
$("#file").addEventListener("change", (e) => {
  if (e.target.files[0]) loadFile(e.target.files[0]);
});
$$("[data-sample]").forEach((button) =>
  button.addEventListener("click", async () => {
    if (busy) return;
    setBusy(true);
    try {
      const response = await fetch(`/samples/${button.dataset.sample}.png`);
      if (!response.ok) throw Error("示例图片加载失败");
      const blob = await response.blob();
      setBusy(false);
      await loadFile(
        new File([blob], `${button.dataset.sample}.png`, { type: "image/png" }),
      );
    } catch (e) {
      toast(e.message);
      setBusy(false);
    }
  }),
);
$("#apply").addEventListener("click", () => processImage(true));
$("#detect").addEventListener("click", () => processImage(false));
$("#aspect").addEventListener("change", markDirty);
$("#block").addEventListener("input", () => {
  $("#block-label").textContent = $("#block").value;
  markDirty();
});
$("#offset").addEventListener("input", () => {
  $("#offset-label").textContent = $("#offset").value;
  markDirty();
});
$$("[data-mode]").forEach((b) =>
  b.addEventListener("click", () => {
    selectedMode = b.dataset.mode;
    showOutput();
  }),
);
function download(url, name) {
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
}
$("#download").addEventListener("click", () => {
  if (!dirty && result?.outputs[selectedMode])
    download(result.outputs[selectedMode], `scanlab-${selectedMode}.png`);
});
$("#metadata").addEventListener("click", () => {
  if (dirty || !result) return;
  const { source, edges, outputs, ...meta } = result;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(meta, null, 2)], { type: "application/json" }),
  );
  download(url, "scanlab-parameters.json");
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
const kindNames = {
  perspective: "透视倾斜",
  shadow: "光照渐变",
  tilted: "旋转纸张",
  blur: "失焦模糊",
  lowcontrast: "低对比度",
  occluded: "边缘遮挡",
};
async function benchmark() {
  try {
    const r = await (await fetch("/api/evaluation")).json();
    if (!r) {
      $("#report").textContent = "请先运行 python -m app.evaluate 生成评测。";
      return;
    }
    $("#report").innerHTML =
      `<div class="bench-note">固定合成开发评测集：24张文档图与4张纯色负例。通过标准为角点平均误差不超过图像对角线的2.5%，且区域IoU不低于0.90。这不是实拍照片效果或OCR识别率。</div><div class="benchmark-grid"><div class="benchmark-card"><span>几何定位通过</span><strong>${r.pass_count} / ${r.case_count}</strong><p>满足误差和区域重合两个条件</p></div><div class="benchmark-card"><span>纯色图片暂不检测</span><strong>${r.blank_rejections} / ${r.blank_count}</strong><p>简单负例，不代表复杂背景表现</p></div><div class="benchmark-card"><span>P95 检测时间</span><strong>${r.p95_detect_ms} ms</strong><p>仅本机轮廓检测，不含解码和图片增强</p></div></div><div class="table-wrap"><table><thead><tr><th>场景</th><th>随机种子</th><th>检测到四边形</th><th>角点归一化误差</th><th>区域 IoU</th><th>是否通过</th></tr></thead><tbody>${r.cases.map((x) => `<tr><td>${kindNames[x.condition]}</td><td>${x.seed}</td><td>${x.detected ? "是" : "否"}</td><td>${x.corner_error_diagonal === null ? "—" : (100 * x.corner_error_diagonal).toFixed(2) + "%"}</td><td>${x.iou.toFixed(3)}</td><td class="${x.pass ? "pass" : "fail"}">${x.pass ? "通过" : "失败，需复核"}</td></tr>`).join("")}</tbody></table></div><p class="learning-note">OpenCV ${r.opencv_version} · 合成数据含人为设定的版式和背景，有明显分布局限。源码中保留全部失败样例；请用自己的照片继续测试。重新评测请运行 check.cmd。</p>`;
  } catch {
    toast("无法载入评测报告");
  }
}
$$("[data-page]").forEach((b) =>
  b.addEventListener("click", () => {
    $$(".page").forEach((p) => (p.hidden = p.id !== b.dataset.page));
    $$("[data-page]").forEach((x) => x.classList.toggle("active", x === b));
    if (b.dataset.page === "benchmark") benchmark();
  }),
);
