class Wheel {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.segments = [];
    this.images = {};
    this.rotation = 0;
    this.pointerAngle = -Math.PI / 2; // pointer fixed at the top
  }

  setSegments(segments) {
    this.segments = segments;
    this.images = {};
    segments.forEach((seg) => {
      if (seg.image) {
        const img = new Image();
        img.onload = () => this.draw();
        img.src = seg.image;
        this.images[seg.id] = img;
      }
    });
    this.draw();
  }

  draw() {
    const { ctx, canvas, segments, rotation } = this;
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const r = Math.min(w, h) / 2 - 8;
    ctx.clearRect(0, 0, w, h);

    const n = segments.length;
    if (!n) return;
    const sliceAngle = (2 * Math.PI) / n;

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(rotation);

    segments.forEach((seg, i) => {
      const start = i * sliceAngle;
      const end = start + sliceAngle;

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, r, start, end);
      ctx.closePath();
      ctx.clip();

      const img = this.images[seg.id];
      if (img && img.complete && img.naturalWidth) {
        ctx.fillStyle = seg.color || "#333";
        ctx.fill();
        const mid = start + sliceAngle / 2;
        const size = r * 0.75;
        const ix = Math.cos(mid) * r * 0.5 - size / 2;
        const iy = Math.sin(mid) * r * 0.5 - size / 2;
        ctx.drawImage(img, ix, iy, size, size);
      } else {
        ctx.fillStyle = seg.color || "#555";
        ctx.fill();
      }
      ctx.restore();

      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, r, start, end);
      ctx.closePath();
      ctx.strokeStyle = "rgba(0,0,0,0.35)";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.save();
      ctx.rotate(start + sliceAngle / 2);
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#fff";
      ctx.font = "bold 14px sans-serif";
      ctx.shadowColor = "rgba(0,0,0,0.7)";
      ctx.shadowBlur = 4;
      ctx.fillText(seg.label, r - 12, 0);
      ctx.restore();
    });

    ctx.restore();

    // pointer triangle, fixed at top
    ctx.save();
    ctx.translate(cx, cy);
    ctx.beginPath();
    ctx.moveTo(-11, -r - 16);
    ctx.lineTo(11, -r - 16);
    ctx.lineTo(0, -r + 8);
    ctx.closePath();
    ctx.fillStyle = "#eef0f7";
    ctx.fill();
    ctx.restore();

    // hub
    ctx.save();
    ctx.translate(cx, cy);
    ctx.beginPath();
    ctx.arc(0, 0, 10, 0, 2 * Math.PI);
    ctx.fillStyle = "#eef0f7";
    ctx.fill();
    ctx.restore();
  }

  spinToSegment(index, onDone) {
    const n = this.segments.length;
    if (!n) return;
    const sliceAngle = (2 * Math.PI) / n;
    const targetCenter = (index + 0.5) * sliceAngle;

    let desiredMod = this.pointerAngle - targetCenter;
    desiredMod = ((desiredMod % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);
    const currentMod = ((this.rotation % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI);

    let delta = desiredMod - currentMod;
    if (delta < 0) delta += 2 * Math.PI;

    const extraSpins = 5;
    const totalDelta = delta + extraSpins * 2 * Math.PI;
    const startRotation = this.rotation;
    const endRotation = this.rotation + totalDelta;
    const duration = 4200;
    const startTime = performance.now();
    const ease = (t) => 1 - Math.pow(1 - t, 3);

    const step = (now) => {
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / duration);
      this.rotation = startRotation + (endRotation - startRotation) * ease(t);
      this.draw();
      if (t < 1) {
        requestAnimationFrame(step);
      } else {
        this.rotation = endRotation;
        this.draw();
        if (onDone) onDone();
      }
    };
    requestAnimationFrame(step);
  }
}
