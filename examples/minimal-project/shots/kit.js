// 所有分镜共用:画面只取决于 t。
(function () {
  const clamp = (v) => Math.min(1, Math.max(0, v));
  const ease = (v) => v * v * (3 - 2 * v);
  const out = (v) => 1 - Math.pow(1 - v, 3);
  const len = () => parseFloat(document.body.dataset.len || "6");
  const nums = (s) => s.split(",").map(Number);
  function wrap(el) {
    const walk = (n) => {
      [...n.childNodes].forEach((c) => {
        if (c.nodeType === 3) {
          const f = document.createDocumentFragment();
          [...c.textContent].forEach((ch) => { const s = document.createElement("span"); s.className = "ch"; s.textContent = ch; f.appendChild(s); });
          n.replaceChild(f, c);
        } else if (c.tagName !== "BR") walk(c);
      });
    };
    walk(el);
    el._ch = [...el.querySelectorAll(".ch")];
  }
  document.querySelectorAll("[data-type]").forEach(wrap);
  function frame(t) {
    document.querySelectorAll("[data-in]").forEach((el) => {
      const a = parseFloat(el.dataset.in), d = parseFloat(el.dataset.fade || "0.5"), dy = parseFloat(el.dataset.dy || "0");
      let o = ease(clamp((t - a) / d));
      const shift = (1 - out(clamp((t - a) / d))) * dy;
      if (el.dataset.out) o *= 1 - ease(clamp((t - parseFloat(el.dataset.out)) / 0.5));
      el.style.opacity = o;
      el.style.translate = `0 ${shift}px`;
    });
    document.querySelectorAll("[data-slide]").forEach((el) => {
      const [a, d, dx, dy] = nums(el.dataset.slide); const u = out(clamp((t - a) / d));
      el.style.translate = `${dx * (1 - u)}px ${dy * (1 - u)}px`;
      el.style.opacity = clamp((t - a) / (d * 0.5));
    });
    document.querySelectorAll("[data-pop]").forEach((el) => {
      const [a, d, s] = nums(el.dataset.pop); const u = out(clamp((t - a) / d));
      el.style.scale = s + (1 - s) * u; el.style.opacity = clamp((t - a) / (d * 0.6));
    });
    document.querySelectorAll("[data-kb]").forEach((el) => {
      const [s0, x0, y0, s1, x1, y1] = nums(el.dataset.kb); const u = clamp(t / len());
      el.style.transform = `translate(${x0 + (x1 - x0) * u}px, ${y0 + (y1 - y0) * u}px) scale(${s0 + (s1 - s0) * u})`;
    });
    document.querySelectorAll("[data-drift]").forEach((el) => {
      const [x0, x1] = nums(el.dataset.drift); el.style.translate = `${x0 + (x1 - x0) * clamp(t / len())}px 0`;
    });
    document.querySelectorAll("[data-wipe]").forEach((el) => {
      const [a, d] = nums(el.dataset.wipe); el.style.setProperty("--w", `${out(clamp((t - a) / d)) * 100}%`);
    });
    document.querySelectorAll("[data-reveal]").forEach((el) => {
      const [a, d] = nums(el.dataset.reveal); el.style.clipPath = `inset(0 ${(1 - out(clamp((t - a) / d))) * 100}% 0 0)`;
    });
    document.querySelectorAll("[data-iris]").forEach((el) => {
      const [a, d] = nums(el.dataset.iris); el.style.clipPath = `circle(${out(clamp((t - a) / d)) * 72}% at 50% 50%)`;
    });
    document.querySelectorAll("[data-erase]").forEach((el) => {
      const [a, d] = nums(el.dataset.erase); const u = ease(clamp((t - a) / d));
      el.style.clipPath = `inset(0 0 0 ${u * 100}%)`; el.style.opacity = 1 - u * 0.5;
    });
    document.querySelectorAll("[data-type]").forEach((el) => {
      const [a, cps] = nums(el.dataset.type);
      el._ch.forEach((c, i) => { c.style.opacity = clamp((t - a - i / cps) * cps); });
    });
    document.querySelectorAll("[data-count]").forEach((el) => {
      const [a, d, v] = nums(el.dataset.count); el.textContent = Math.round(out(clamp((t - a) / d)) * v);
      el.style.opacity = clamp((t - a) / 0.2);
    });
    document.querySelectorAll("[data-draw]").forEach((el) => {
      const [a, d] = nums(el.dataset.draw);
      el.style.strokeDasharray = 1; el.style.strokeDashoffset = 1 - ease(clamp((t - a) / d));
    });
  }
  const ready = () => Promise.all([...document.images].map((im) => im.decode().catch(() => {}))).then(() => document.fonts.ready);
  window.film = { frame, ready };
})();

(function () {
  const clamp = (v) => Math.min(1, Math.max(0, v)), ease = (v) => v * v * (3 - 2 * v), out = (v) => 1 - Math.pow(1 - v, 3);
  const nums = (s) => s.split(",").map(Number), base = window.film.frame;
  window.film.frame = function (t) {
    base(t);
    document.querySelectorAll("[data-span]").forEach((el) => { const [a, b] = nums(el.dataset.span); el.style.opacity = clamp((t - a) / .12) * (1 - clamp((t - b) / .12)); });
    document.querySelectorAll("[data-vreveal]").forEach((el) => { const [a, d] = nums(el.dataset.vreveal); el.style.clipPath = `inset(0 0 ${(1 - out(clamp((t - a) / d))) * 100}% 0)`; });
    document.querySelectorAll("[data-r]").forEach((el) => { const [a, d, r0, r1] = nums(el.dataset.r); el.setAttribute("r", r0 + (r1 - r0) * ease(clamp((t - a) / d))); });
    document.querySelectorAll("[data-dip]").forEach((el) => { const [a, b, c, d] = nums(el.dataset.dip); el.style.opacity = ease(clamp((t - a) / (b - a))) * (1 - ease(clamp((t - c) / (d - c)))); });
    document.querySelectorAll("[data-move]").forEach((el) => { const [a, d, x0, x1] = nums(el.dataset.move); el.style.translate = `${x0 + (x1 - x0) * clamp((t - a) / d)}px 0`; });
  };
})();
