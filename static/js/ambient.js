// Ambient Particle Field (DESIGN.md): sparse outlined triangles drifting at low
// opacity behind every page. Skipped on the dashboard, whose constellation
// already fills that role, and frozen when reduced motion is requested.
(() => {
  const canvas = document.getElementById("ambient-field");
  if (!canvas || document.getElementById("constellation")) return;
  const ctx = canvas.getContext("2d");
  const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const COLORS = ["#8052ff", "#ffb829", "#15846e", "#3ecfae", "#ff5fa2", "#5aa9ff"];
  let seed = 11;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  const bits = Array.from({ length: 70 }, () => ({
    x: rand(), y: rand(), size: 1.5 + rand() * 3, rot: rand() * 6.28,
    vx: (rand() - 0.5) * 0.00006, vy: (rand() - 0.5) * 0.00006, spin: (rand() - 0.5) * 0.004,
    color: COLORS[Math.floor(rand() * COLORS.length)], alpha: 0.12 + rand() * 0.22,
  }));
  let W = 0, H = 0;
  function size() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function draw() {
    ctx.clearRect(0, 0, W, H);
    ctx.lineWidth = 1;
    bits.forEach((b) => {
      if (!still) {
        b.x = (b.x + b.vx + 1) % 1; b.y = (b.y + b.vy + 1) % 1; b.rot += b.spin;
      }
      ctx.globalAlpha = b.alpha;
      ctx.strokeStyle = b.color;
      ctx.beginPath();
      for (let k = 0; k < 3; k++) {
        const a = b.rot + (k * 2 * Math.PI) / 3;
        const px = b.x * W + Math.cos(a) * b.size, py = b.y * H + Math.sin(a) * b.size;
        k ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
      }
      ctx.closePath();
      ctx.stroke();
    });
    if (!still) requestAnimationFrame(draw);
  }
  window.addEventListener("resize", () => { size(); if (still) draw(); });
  size();
  draw();
})();
