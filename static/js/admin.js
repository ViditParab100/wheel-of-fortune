document.addEventListener("DOMContentLoaded", () => {
  let segments = JSON.parse(document.getElementById("initial-segments").textContent);

  const segmentsList = document.getElementById("segments-list");
  const segmentsMsg = document.getElementById("segments-msg");
  const windowMsg = document.getElementById("window-msg");
  const windowStartInput = document.getElementById("window-start");
  const windowEndInput = document.getElementById("window-end");

  function setMsg(el, text, type) {
    el.textContent = text || "";
    el.className = "msg" + (type ? " " + type : "");
  }

  function escapeHtml(str) {
    return (str || "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function renderSegments() {
    segmentsList.innerHTML = "";
    segments.forEach((seg) => {
      const row = document.createElement("div");
      row.className = "seg-row";
      row.dataset.id = seg.id;
      row.innerHTML = `
        <input type="color" class="seg-color" value="${seg.color || "#999999"}" />
        <input type="text" class="seg-label" placeholder="Label (shown on wheel)" value="${escapeHtml(seg.label)}" />
        <input type="text" class="seg-prize" placeholder="Prize text" value="${escapeHtml(seg.prize)}" />
        <input type="number" class="seg-weight" min="0" value="${seg.weight}" title="Relative odds weight" />
        <input type="file" class="seg-image" accept="image/png" title="Upload PNG for this wedge" />
        ${seg.image ? `<img src="${seg.image}" alt="" width="32" height="32" style="border-radius:6px;object-fit:cover;" />` : ""}
        <button type="button" class="secondary seg-remove">Remove</button>
      `;
      segmentsList.appendChild(row);

      row.querySelector(".seg-image").addEventListener("change", (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const fd = new FormData();
        fd.append("image", file);
        fetch(`/admin/segments/${seg.id}/image`, { method: "POST", body: fd })
          .then((r) => r.json())
          .then((data) => {
            if (data.ok) {
              segments = data.segments;
              renderSegments();
              setMsg(segmentsMsg, "Image uploaded.", "ok");
            } else {
              setMsg(segmentsMsg, data.error, "error");
            }
          });
      });

      row.querySelector(".seg-remove").addEventListener("click", () => {
        segments = segments.filter((s) => s.id !== seg.id);
        renderSegments();
        saveSegments();
      });
    });
  }

  function collectSegments() {
    return Array.from(segmentsList.children).map((row) => {
      const id = row.dataset.id;
      const existing = segments.find((s) => s.id === id);
      return {
        id,
        color: row.querySelector(".seg-color").value,
        label: row.querySelector(".seg-label").value,
        prize: row.querySelector(".seg-prize").value,
        weight: parseInt(row.querySelector(".seg-weight").value, 10) || 0,
        image: existing ? existing.image : null,
      };
    });
  }

  function saveSegments() {
    return fetch("/admin/segments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ segments: collectSegments() }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) {
          segments = data.segments;
          renderSegments();
          setMsg(segmentsMsg, "Saved.", "ok");
        } else {
          setMsg(segmentsMsg, data.error, "error");
        }
      });
  }

  document.getElementById("btn-add-segment").addEventListener("click", () => {
    segments.push({
      id: Math.random().toString(16).slice(2, 10),
      label: "New Prize",
      prize: "New Prize",
      weight: 1,
      color: "#999999",
      image: null,
    });
    renderSegments();
    saveSegments();
  });

  document.getElementById("btn-save-segments").addEventListener("click", saveSegments);

  renderSegments();

  function toIsoNaive(value) {
    if (!value) return null;
    return value.length === 16 ? value + ":00" : value;
  }

  function postWindow(body) {
    fetch("/admin/window", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.ok) {
          setMsg(windowMsg, "Saved, reloading...", "ok");
          setTimeout(() => location.reload(), 600);
        } else {
          setMsg(windowMsg, data.error, "error");
        }
      });
  }

  document.getElementById("btn-open-new").addEventListener("click", () => {
    if (!confirm("Start a brand-new window? This lets every player spin again, including ones who already spun.")) return;
    postWindow({
      action: "open_new_window",
      window_start: toIsoNaive(windowStartInput.value) || new Date().toISOString().slice(0, 19),
      window_end: toIsoNaive(windowEndInput.value),
    });
  });

  document.getElementById("btn-update-times").addEventListener("click", () => {
    postWindow({
      action: "update_times",
      window_start: toIsoNaive(windowStartInput.value),
      window_end: toIsoNaive(windowEndInput.value),
    });
  });

  const closeBtn = document.getElementById("btn-close-now");
  if (closeBtn) closeBtn.addEventListener("click", () => postWindow({ action: "close_now" }));

  const reopenBtn = document.getElementById("btn-reopen");
  if (reopenBtn) reopenBtn.addEventListener("click", () => postWindow({ action: "reopen" }));
});
