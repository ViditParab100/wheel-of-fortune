document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("wheel");
  const wheel = new Wheel(canvas);

  const statusMsg = document.getElementById("status-msg");
  const verifyForm = document.getElementById("verify-form");
  const verifyMsg = document.getElementById("verify-msg");
  const wheelWrap = document.getElementById("wheel-wrap");
  const spinBtn = document.getElementById("spin-btn");
  const resultBanner = document.getElementById("result-banner");

  let segments = [];
  let windowOpen = false;

  function setMsg(el, text, type) {
    el.textContent = text || "";
    el.className = "msg" + (type ? " " + type : "");
  }

  function loadSegments() {
    return fetch("/api/segments")
      .then((r) => r.json())
      .then((data) => {
        segments = data;
        wheel.setSegments(segments);
      });
  }

  function loadStatus() {
    return fetch("/api/status")
      .then((r) => r.json())
      .then((data) => {
        windowOpen = data.open;
        if (!windowOpen) {
          setMsg(statusMsg, "The spin window is currently closed. Check back later.", "error");
        } else {
          setMsg(statusMsg, "The spin window is open — verify your Torn key to spin.", "ok");
        }
      });
  }

  loadSegments();
  loadStatus();

  verifyForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const apiKey = document.getElementById("api-key").value.trim();
    const submitBtn = verifyForm.querySelector("button");
    submitBtn.disabled = true;
    setMsg(verifyMsg, "Checking with Torn...", null);

    fetch("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey }),
    })
      .then((r) => r.json().then((data) => ({ status: r.status, data })))
      .then(({ data }) => {
        submitBtn.disabled = false;
        if (!data.ok) {
          setMsg(verifyMsg, data.error, "error");
          return;
        }
        setMsg(verifyMsg, `Welcome, ${data.torn_name}! Give it a spin.`, "ok");
        document.getElementById("api-key").value = "";
        verifyForm.classList.add("hidden");
        wheelWrap.classList.remove("hidden");
      })
      .catch(() => {
        submitBtn.disabled = false;
        setMsg(verifyMsg, "Something went wrong. Try again.", "error");
      });
  });

  spinBtn.addEventListener("click", () => {
    spinBtn.disabled = true;
    resultBanner.classList.add("hidden");

    fetch("/api/spin", { method: "POST" })
      .then((r) => r.json().then((data) => ({ status: r.status, data })))
      .then(({ data }) => {
        if (!data.ok) {
          setMsg(verifyMsg, data.error, "error");
          spinBtn.disabled = false;
          return;
        }
        const index = segments.findIndex((s) => s.id === data.segment_id);
        wheel.spinToSegment(index < 0 ? 0 : index, () => {
          resultBanner.textContent = `You won: ${data.prize}`;
          resultBanner.classList.remove("hidden");
        });
      })
      .catch(() => {
        setMsg(verifyMsg, "Something went wrong. Try again.", "error");
        spinBtn.disabled = false;
      });
  });
});
