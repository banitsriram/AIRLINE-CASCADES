// The airline network drawn as a constellation of outlined triangles.
// Each airport is a cluster placed at its real position; particles drift along
// routes; airports with late departures burn amber. Hover shows the airport,
// click opens its board. Everything is also reachable via the chip links below.
(() => {
  const root = document.getElementById("constellation");
  if (!root) return;

  const airports = JSON.parse(root.dataset.airports);
  const routes = JSON.parse(root.dataset.routes);
  const canvas = root.querySelector("canvas");
  const tip = root.querySelector(".constellation-tip");
  const ctx = canvas.getContext("2d");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // [longitude, latitude]; airports added later without an entry sit on a ring.
  const COORDS = {
    DEL: [77.1, 28.56], BOM: [72.87, 19.09], BLR: [77.71, 13.2], MAA: [80.17, 12.99],
    CCU: [88.45, 22.65], HYD: [78.43, 17.24], PNQ: [73.92, 18.58], GOI: [73.83, 15.38],
    AMD: [72.63, 23.07], COK: [76.39, 10.15], LKO: [80.89, 26.76], JAI: [75.81, 26.82],
    TRV: [76.92, 8.48], IXC: [76.79, 30.67], PAT: [85.09, 25.59], BBI: [85.82, 20.25],
    GAU: [91.59, 26.11], NAG: [79.05, 21.09], IXB: [88.33, 26.68], VNS: [82.86, 25.45],
  };
  const SPECTRUM = ["#8052ff", "#a386ff", "#3ecfae", "#15846e", "#ff5fa2", "#5aa9ff"];
  const AMBER = "#ffb829";

  // Deterministic pseudo-random so the constellation keeps its shape between reloads.
  let seed = 7;
  const rand = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  const gauss = () => {
    let u = 0, v = 0;
    while (!u) u = rand();
    while (!v) v = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };

  const degree = {};
  routes.forEach(([a, b]) => { degree[a] = (degree[a] || 0) + 1; degree[b] = (degree[b] || 0) + 1; });
  const byId = Object.fromEntries(airports.map((a) => [a.id, a]));
  const neighbours = {};
  routes.forEach(([a, b]) => {
    (neighbours[a] = neighbours[a] || new Set()).add(b);
    (neighbours[b] = neighbours[b] || new Set()).add(a);
  });

  airports.forEach((a, i) => {
    const c = COORDS[a.iata];
    a.lon = c ? c[0] : 80 + 9 * Math.cos((i / airports.length) * 2 * Math.PI);
    a.lat = c ? c[1] : 20 + 9 * Math.sin((i / airports.length) * 2 * Math.PI);
    // Busier airports (more routes, more departures) get bigger, denser clusters.
    a.count = Math.min(170, Math.round(22 + (degree[a.id] || 1) * 4 + a.deps * 1.5));
    a.spread = 3 + Math.sqrt(a.count) * 0.95;
    // Amber share grows with the airport's late departures.
    const lateShare = a.late ? Math.min(0.65, 0.15 + a.late * 0.05) : 0;
    a.particles = Array.from({ length: a.count }, () => ({
      dx: gauss() * a.spread,
      dy: gauss() * a.spread,
      size: 1.6 + rand() * 3.4,
      rot: rand() * Math.PI * 2,
      phase: rand() * Math.PI * 2,
      speed: 0.3 + rand() * 0.7,
      color: rand() < lateShare ? AMBER : SPECTRUM[Math.floor(rand() * SPECTRUM.length)],
      sx: rand(), sy: rand(), // scattered start, for the entrance
      ox: 0, oy: 0, // eased push-away from the cursor
    }));
    a.vis = 1;   // eased visibility: fades when another airport is hovered
    a.glow = 0;  // eased hover emphasis
    a.burst = 0; // click burst, 0..1
  });

  const streams = [];
  routes.forEach(([a, b]) => {
    if (!byId[a] || !byId[b]) return;
    const n = 2 + Math.floor(rand() * 3);
    for (let i = 0; i < n; i++) {
      streams.push({
        a: byId[a], b: byId[b], t: rand(), speed: 0.0006 + rand() * 0.0012,
        bend: (rand() - 0.5) * 0.35, size: 1.4 + rand() * 1.8,
        color: SPECTRUM[Math.floor(rand() * SPECTRUM.length)], reverse: rand() < 0.5,
      });
    }
  });

  const ambient = Array.from({ length: 110 }, () => ({
    x: rand(), y: rand(), size: 1.2 + rand() * 2.4, rot: rand() * 6.28,
    phase: rand() * 6.28, color: SPECTRUM[Math.floor(rand() * SPECTRUM.length)],
    ox: 0, oy: 0,
  }));

  let W = 0, H = 0, hovered = null;
  const lons = airports.map((a) => a.lon), lats = airports.map((a) => a.lat);
  const bounds = {
    minLon: Math.min(...lons) - 1.5, maxLon: Math.max(...lons) + 1.5,
    minLat: Math.min(...lats) - 1.5, maxLat: Math.max(...lats) + 1.5,
  };

  function layout() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = root.clientWidth; H = root.clientHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const pad = 36;
    const sx = (W - pad * 2) / (bounds.maxLon - bounds.minLon);
    const sy = (H - pad * 2) / (bounds.maxLat - bounds.minLat);
    const s = Math.min(sx, sy);
    const ox = (W - s * (bounds.maxLon - bounds.minLon)) / 2;
    const oy = (H - s * (bounds.maxLat - bounds.minLat)) / 2;
    const scale = Math.max(0.55, Math.min(1.1, W / 640));
    airports.forEach((a) => {
      a.x = ox + (a.lon - bounds.minLon) * s;
      a.y = oy + (bounds.maxLat - a.lat) * s;
      a.scale = scale;
    });
  }

  function tri(path, x, y, size, rot) {
    for (let k = 0; k < 3; k++) {
      const ang = rot + (k * 2 * Math.PI) / 3;
      const px = x + Math.cos(ang) * size, py = y + Math.sin(ang) * size;
      k ? path.lineTo(px, py) : path.moveTo(px, py);
    }
    path.closePath();
  }

  const ease = (t) => 1 - Math.pow(1 - Math.min(1, t), 3);
  const start = performance.now();
  const pointer = { x: 0, y: 0, active: false };
  let focus = null;    // airport whose network is highlighted (kept while fading out)
  let hoverMix = 0;    // eased 0..1: how strongly the highlight is showing
  let leaving = false; // a click is navigating away

  const approach = (from, to, k) => from + (to - from) * k;
  const isLinked = (a) => focus && (a === focus || neighbours[focus.id]?.has(a.id));

  // Push a point away from the cursor; returns the eased offset stored on p.
  function repel(p, x, y, radius, strength) {
    let tx = 0, ty = 0;
    if (pointer.active && !reduceMotion) {
      const dx = x - pointer.x, dy = y - pointer.y;
      const d = Math.hypot(dx, dy);
      if (d < radius && d > 0.01) {
        const f = Math.pow(1 - d / radius, 2) * strength;
        tx = (dx / d) * f; ty = (dy / d) * f;
      }
    }
    p.ox = approach(p.ox, tx, 0.16);
    p.oy = approach(p.oy, ty, 0.16);
  }

  function frame() {
    // performance.now() rather than the rAF timestamp: some browsers hand rAF a
    // timestamp from an earlier origin, which stalls the entrance.
    const time = (performance.now() - start) / 1000;
    const enter = reduceMotion ? 1 : ease(time / 1.8);
    const k = reduceMotion ? 1 : 0.12;

    hoverMix = approach(hoverMix, hovered ? 1 : 0, k);
    if (hovered) focus = hovered;
    else if (hoverMix < 0.02) focus = null;
    airports.forEach((a) => {
      a.vis = approach(a.vis, !focus || isLinked(a) ? 1 : 0.22, k);
      a.glow = approach(a.glow, a === hovered ? 1 : 0, k);
      if (a.burst) a.burst = Math.min(1, a.burst + 0.07);
    });

    ctx.clearRect(0, 0, W, H);
    const paths = new Map(); // "color|alpha" -> Path2D, so each colour is stroked once
    const pathFor = (color, alpha) => {
      const key = color + "|" + Math.round(Math.max(0, Math.min(1, alpha)) * 20) / 20;
      if (!paths.has(key)) paths.set(key, new Path2D());
      return paths.get(key);
    };

    ambient.forEach((p) => {
      const drift = reduceMotion ? 0 : Math.sin(time * 0.2 + p.phase) * 6;
      const x = p.x * W + drift, y = p.y * H + drift * 0.6;
      repel(p, x, y, 110, 34);
      tri(pathFor(p.color, 0.22), x + p.ox, y + p.oy, p.size, p.rot + time * 0.05);
    });

    // Faint arcs from the focused airport to every airport it serves.
    if (focus && hoverMix > 0.01) {
      ctx.lineWidth = 1;
      neighbours[focus.id]?.forEach((id) => {
        const b = byId[id];
        if (!b) return;
        const mx = (focus.x + b.x) / 2 - (b.y - focus.y) * 0.12;
        const my = (focus.y + b.y) / 2 + (b.x - focus.x) * 0.12;
        ctx.globalAlpha = 0.28 * hoverMix * enter;
        ctx.strokeStyle = b.late ? AMBER : "#a386ff";
        ctx.beginPath();
        ctx.moveTo(focus.x, focus.y);
        ctx.quadraticCurveTo(mx, my, b.x, b.y);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    streams.forEach((s) => {
      const onFocus = focus && (s.a === focus || s.b === focus);
      if (!reduceMotion) s.t = (s.t + s.speed * (onFocus ? 1 + 2 * hoverMix : 1)) % 1;
      const t = s.reverse ? 1 - s.t : s.t;
      const mx = (s.a.x + s.b.x) / 2 - (s.b.y - s.a.y) * s.bend;
      const my = (s.a.y + s.b.y) / 2 + (s.b.x - s.a.x) * s.bend;
      const x = (1 - t) * (1 - t) * s.a.x + 2 * (1 - t) * t * mx + t * t * s.b.x;
      const y = (1 - t) * (1 - t) * s.a.y + 2 * (1 - t) * t * my + t * t * s.b.y;
      const base = Math.sin(Math.PI * t) > 0.5 ? 0.55 : 0.25;
      const alpha = onFocus ? approach(base, 1, hoverMix) : base * (1 - 0.8 * hoverMix);
      tri(pathFor(s.color, alpha), x, y, s.size * (onFocus ? 1 + 0.4 * hoverMix : 1), t * 6);
    });

    airports.forEach((a) => {
      const swell = 1 + 0.22 * a.glow + 2.2 * ease(a.burst);
      const spin = reduceMotion ? 0 : time * (0.15 + 0.9 * a.glow);
      const alpha = (0.3 + 0.6 * a.vis) * (1 - a.burst);
      a.particles.forEach((p) => {
        const wob = reduceMotion ? 0 : Math.sin(time * p.speed + p.phase) * 1.6;
        const tx = a.x + p.dx * a.scale * swell + wob, ty = a.y + p.dy * a.scale * swell - wob;
        const bx = p.sx * W + (tx - p.sx * W) * enter;
        const by = p.sy * H + (ty - p.sy * H) * enter;
        repel(p, bx, by, a === hovered ? 40 : 80, a === hovered ? 10 : 26);
        tri(pathFor(p.color, alpha), bx + p.ox, by + p.oy, p.size * (1 + 0.25 * a.glow), p.rot + spin * p.speed);
      });
    });

    ctx.lineWidth = 1;
    ctx.lineJoin = "miter";
    for (const [key, path] of paths) {
      const [color, alpha] = key.split("|");
      if (Number(alpha) === 0) continue;
      ctx.globalAlpha = Number(alpha);
      ctx.strokeStyle = color;
      ctx.stroke(path);
    }
    ctx.globalAlpha = 1;

    // Airport codes, fading in once the clusters have formed.
    ctx.textBaseline = "middle";
    ctx.lineJoin = "round";
    ctx.lineWidth = 4;
    ctx.strokeStyle = "#000";
    airports.forEach((a) => {
      const lx = a.x + a.spread * a.scale * (1.6 + 0.35 * a.glow) + 4;
      ctx.font = `600 ${11 + 3 * a.glow}px Inter, system-ui, sans-serif`;
      ctx.globalAlpha = enter * (0.35 + 0.65 * a.vis);
      ctx.strokeText(a.iata, lx, a.y);
      ctx.fillStyle = a.glow > 0.5 ? "#ffffff" : a.late ? AMBER : "#bdbdbd";
      ctx.fillText(a.iata, lx, a.y);
    });
    ctx.globalAlpha = 1;

    if (!reduceMotion) requestAnimationFrame(frame);
  }

  function airportAt(x, y) {
    let best = null, bestD = Infinity;
    airports.forEach((a) => {
      const d = Math.hypot(a.x - x, a.y - y);
      if (d < Math.max(40, a.spread * a.scale * 2.4) && d < bestD) { best = a; bestD = d; }
    });
    return best;
  }

  function showTip(a) {
    const routesCount = neighbours[a.id]?.size || 0;
    tip.replaceChildren(`${a.iata}  ${a.city}`);
    const sub = document.createElement("span");
    const parts = [`${a.deps} departures today`];
    if (a.late) parts.push(`${a.late} running late`);
    parts.push(`${routesCount} ${routesCount === 1 ? "route" : "routes"}`);
    sub.textContent = parts.join(", ");
    tip.append(sub);
    tip.classList.toggle("is-late", a.late > 0);
    tip.style.left = a.x + "px";
    tip.style.top = a.y - a.spread * a.scale * 1.3 + "px";
    tip.style.opacity = 1;
  }

  function onMove(evt) {
    const r = canvas.getBoundingClientRect();
    pointer.x = evt.clientX - r.left;
    pointer.y = evt.clientY - r.top;
    pointer.active = true;
    const a = airportAt(pointer.x, pointer.y);
    if (a !== hovered && !leaving) {
      hovered = a;
      canvas.style.cursor = a ? "pointer" : "default";
      a ? showTip(a) : (tip.style.opacity = 0);
    }
    if (reduceMotion) requestAnimationFrame(frame);
  }

  canvas.addEventListener("pointermove", onMove);
  canvas.addEventListener("pointerdown", onMove);
  canvas.addEventListener("pointerleave", () => {
    pointer.active = false;
    if (leaving) return;
    hovered = null; tip.style.opacity = 0; canvas.style.cursor = "default";
    if (reduceMotion) requestAnimationFrame(frame);
  });
  canvas.addEventListener("click", (evt) => {
    const r = canvas.getBoundingClientRect();
    const a = airportAt(evt.clientX - r.left, evt.clientY - r.top);
    if (!a || leaving) return;
    if (reduceMotion) { window.location.href = a.url; return; }
    leaving = true;
    a.burst = 0.01;
    setTimeout(() => { window.location.href = a.url; }, 320);
  });
  // Coming back via the browser's back button restores the page from cache mid-burst.
  window.addEventListener("pageshow", (evt) => {
    if (!evt.persisted) return;
    leaving = false;
    airports.forEach((a) => { a.burst = 0; });
  });

  new ResizeObserver(() => { layout(); if (reduceMotion) requestAnimationFrame(frame); }).observe(root);
  layout();
  requestAnimationFrame(frame);
})();
