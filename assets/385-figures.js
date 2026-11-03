/* Worksheet 385, "שכפול האייקונים": the right trapezoid and its three copies (SOURCE_OF_TRUTH §כג.19).
   Every vertex is computed from the given lengths (bases 3 and 5 cm, the right leg 3 cm) by the
   transformation the text describes, and both figures share one scale, so the copies are exactly congruent. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var U = 5.6;                                   // mm per centimetre of the problem
  var A = [[0, 0], [5, 0], [3, 3], [0, 3]];      // right angles at (0,0) and (0,3); P is the lower right vertex
  var P = [5, 0];
  var DOWN = 4.6;                                // the text gives no distance for the move down
  var mirror = function (p) { return [-p[0], p[1]]; };                              // in the right leg x = 0
  var down = function (p) { return [p[0], p[1] - DOWN]; };
  var turn = function (p) { return [P[0] + (p[1] - P[1]), P[1] - (p[0] - P[0])]; };   // 90° clockwise about P
  var TONE = {
    a: { fill: "#dce8f8", line: "#1f4e8c", ink: "#173f74" },
    b: { fill: "#daf1e3", line: "#1d7646", ink: "#155c36" },
    c: { fill: "#fde9cf", line: "#a85b0c", ink: "#874807" },
    d: { fill: "#ebe1f8", line: "#683ca4", ink: "#532e86" }
  };
  var ACT = "#c2410c";                           // the operations: mirror line, move, turn
  var INK = "#1e293b";
  var SCENES = {
    icons: {
      view: [-5.75, -DOWN - 0.75, 8.75, 5.7], dots: true,
      shapes: [["א׳", A, "a"], ["ב׳", A.map(mirror), "b"], ["ג׳", A.map(down), "c"], ["ד׳", A.map(turn), "d"]],
      dashed: [[0, -0.5], [0, 3.5]],
      move: true,
      arc: { c: P, r: 1.9, from: 180, to: 90, text: "90°", at: [106, 2.62] },
      points: [["P", P, [0.42, -0.5]]]
    },
    base: {
      view: [-2.95, -1.3, 5.3, 4.15],         // the measures only; P belongs to the story figure
      shapes: [["א׳", A, "a"]],
      dims: [[[0, 3], [3, 3], [0, 0.62], "3 ס״מ"], [[0, 0], [5, 0], [0, -0.66], "5 ס״מ"], [[0, 0], [0, 3], [-0.62, 0], "3 ס״מ"]]
    }
  };

  function el(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (parent) parent.appendChild(e);
    return e;
  }
  function centroid(pts) {
    var a = 0, x = 0, y = 0;
    pts.forEach(function (p, i) {
      var q = pts[(i + 1) % pts.length], c = p[0] * q[1] - q[0] * p[1];
      a += c; x += (p[0] + q[0]) * c; y += (p[1] + q[1]) * c;
    });
    return [x / (3 * a), y / (3 * a)];
  }
  function dir(p, q) { var dx = q[0] - p[0], dy = q[1] - p[1], l = Math.hypot(dx, dy); return [dx / l, dy / l]; }

  function draw(svg, s) {
    var v = s.view, w = (v[2] - v[0]) * U, h = (v[3] - v[1]) * U;
    var X = function (x) { return +((x - v[0]) * U).toFixed(2); };
    var Y = function (y) { return +((v[3] - y) * U).toFixed(2); };
    var at = function (p) { return X(p[0]) + "," + Y(p[1]); };
    svg.setAttribute("viewBox", "0 0 " + w.toFixed(2) + " " + h.toFixed(2));
    svg.setAttribute("width", w.toFixed(2) + "mm");
    svg.setAttribute("height", h.toFixed(2) + "mm");
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var g = el("g", { "font-family": "Arial, 'Noto Sans Hebrew', sans-serif" }, svg);
    function text(str, p, size, color, opts) {
      opts = opts || {};
      var t = el("text", { x: X(p[0]), y: Y(p[1]), "font-size": size, fill: color, "text-anchor": "middle",
        "dominant-baseline": "central", "font-weight": opts.weight || 700 }, g);
      t.style.direction = /[֐-׿]/.test(str) ? "rtl" : "ltr";
      if (opts.italic) { t.setAttribute("font-style", "italic"); t.setAttribute("font-family", "'Times New Roman', Times, serif"); }
      if (opts.halo) { t.setAttribute("stroke", "#fff"); t.setAttribute("stroke-width", opts.halo); t.setAttribute("paint-order", "stroke"); t.setAttribute("stroke-linejoin", "round"); }
      t.textContent = str;
      return t;
    }
    function head(tip, d, color, len, half) {    // a filled arrowhead whose tip is at `tip`, pointing along d
      var b = [tip[0] - d[0] * len, tip[1] - d[1] * len], n = [-d[1] * half, d[0] * half];
      el("polygon", { points: at(tip) + " " + at([b[0] + n[0], b[1] + n[1]]) + " " + at([b[0] - n[0], b[1] - n[1]]), fill: color }, g);
    }
    if (s.dots) {
      el("rect", { x: 0.3, y: 0.3, width: (w - 0.6).toFixed(2), height: (h - 0.6).toFixed(2), rx: 3.2, fill: "#f8fafc", stroke: "#d5deea", "stroke-width": 0.35 }, g);
      for (var gx = Math.ceil(v[0]); gx <= v[2]; gx++)
        for (var gy = Math.ceil(v[1]); gy <= v[3]; gy++)
          el("circle", { cx: X(gx), cy: Y(gy), r: 0.32, fill: "#b8c4d6" }, g);
    }
    s.shapes.forEach(function (sh) {
      var tone = TONE[sh[2]], pts = sh[1];
      el("polygon", { points: pts.map(at).join(" "), fill: tone.fill, stroke: tone.line, "stroke-width": 0.5, "stroke-linejoin": "round" }, g);
      pts.forEach(function (p, i) {           // right-angle marks wherever two sides meet at 90°
        var e1 = dir(p, pts[(i + pts.length - 1) % pts.length]), e2 = dir(p, pts[(i + 1) % pts.length]), k = 0.4;
        if (Math.abs(e1[0] * e2[0] + e1[1] * e2[1]) > 1e-9) return;
        el("path", { d: "M" + at([p[0] + e1[0] * k, p[1] + e1[1] * k]) + "L" + at([p[0] + (e1[0] + e2[0]) * k, p[1] + (e1[1] + e2[1]) * k]) +
          "L" + at([p[0] + e2[0] * k, p[1] + e2[1] * k]), fill: "none", stroke: tone.line, "stroke-width": 0.3 }, g);
      });
    });
    if (s.dashed) {
      el("line", { x1: X(s.dashed[0][0]), y1: Y(s.dashed[0][1]), x2: X(s.dashed[1][0]), y2: Y(s.dashed[1][1]),
        stroke: ACT, "stroke-width": 0.75, "stroke-dasharray": "2.1 1.5", "stroke-linecap": "round" }, g);
    }
    (s.dims || []).forEach(function (dm) {      // dimension line with extension lines and arrowheads
      var p = dm[0], q = dm[1], o = dm[2], u = dir([0, 0], o), d = dir(p, q);
      var p1 = [p[0] + o[0], p[1] + o[1]], q1 = [q[0] + o[0], q[1] + o[1]];
      [p, q].forEach(function (r) {
        el("line", { x1: X(r[0] + u[0] * 0.14), y1: Y(r[1] + u[1] * 0.14), x2: X(r[0] + o[0] + u[0] * 0.22), y2: Y(r[1] + o[1] + u[1] * 0.22),
          stroke: "#64748b", "stroke-width": 0.22 }, g);
      });
      el("line", { x1: X(p1[0]), y1: Y(p1[1]), x2: X(q1[0]), y2: Y(q1[1]), stroke: "#475569", "stroke-width": 0.28 }, g);
      head(p1, [-d[0], -d[1]], "#475569", 0.3, 0.1);
      head(q1, d, "#475569", 0.3, 0.1);
      var mid = [(p1[0] + q1[0]) / 2, (p1[1] + q1[1]) / 2];
      var t = text(dm[3], mid, 3.6, INK, { weight: 700 });
      var b = t.getBBox();
      if (Math.abs(d[0]) < 1e-9) {               // beside an upright dimension line, never across the shape
        var dx = -(b.width / 2 + 1.8);
        t.setAttribute("x", (+t.getAttribute("x") + dx).toFixed(2)); b = t.getBBox();
      }
      g.insertBefore(el("rect", { x: (b.x - 1.1).toFixed(2), y: (b.y - 0.35).toFixed(2), width: (b.width + 2.2).toFixed(2), height: (b.height + 0.7).toFixed(2), rx: 1.2, fill: "#fff" }), t);
    });
    if (s.move) {                                // the move down, from the label of א׳ to the label of ג׳
      var c0 = centroid(s.shapes[0][1]), c1 = centroid(s.shapes[2][1]);
      var a0 = [c0[0], c0[1] - 0.62], a1 = [c1[0], c1[1] + 0.6];
      el("line", { x1: X(a0[0]), y1: Y(a0[1]), x2: X(a1[0]), y2: Y(a1[1] + 0.3), stroke: "#fff", "stroke-width": 2.2, "stroke-linecap": "round" }, g);
      el("line", { x1: X(a0[0]), y1: Y(a0[1]), x2: X(a1[0]), y2: Y(a1[1] + 0.3), stroke: ACT, "stroke-width": 0.75, "stroke-linecap": "round" }, g);
      head(a1, [0, -1], ACT, 0.5, 0.24);
    }
    if (s.arc) {                                 // the quarter turn, clockwise about P
      var r = s.arc.r, c = s.arc.c, rad = Math.PI / 180, lead = 0.5 / r;
      var start = [c[0] + r * Math.cos(s.arc.from * rad), c[1] + r * Math.sin(s.arc.from * rad)];
      var endA = s.arc.to * rad + lead, end = [c[0] + r * Math.cos(endA), c[1] + r * Math.sin(endA)];
      var tip = [c[0] + r * Math.cos(s.arc.to * rad), c[1] + r * Math.sin(s.arc.to * rad)];
      var path = "M" + at(start) + "A" + (r * U).toFixed(2) + "," + (r * U).toFixed(2) + " 0 0 1 " + at(end);
      el("path", { d: path, fill: "none", stroke: "#fff", "stroke-width": 2.1, "stroke-linecap": "round" }, g);
      el("path", { d: path, fill: "none", stroke: ACT, "stroke-width": 0.75, "stroke-linecap": "round" }, g);
      head(tip, dir(end, tip), ACT, 0.5, 0.24);
      var la = s.arc.at[0] * rad, lr = s.arc.at[1];
      text(s.arc.text, [c[0] + lr * Math.cos(la), c[1] + lr * Math.sin(la)], 3.9, ACT, { halo: 1.3 });
    }
    s.shapes.forEach(function (sh) {             // shape names last, above every line
      text(sh[0], centroid(sh[1]), 5, TONE[sh[2]].ink, { weight: 800, halo: 1.1 });
    });
    (s.points || []).forEach(function (pt) {
      el("circle", { cx: X(pt[1][0]), cy: Y(pt[1][1]), r: 0.95, fill: INK, stroke: "#fff", "stroke-width": 0.45 }, g);
      text(pt[0], [pt[1][0] + pt[2][0], pt[1][1] + pt[2][1]], 4.6, INK, { italic: true, halo: 1.2 });
    });
  }

  function render() {
    document.querySelectorAll("svg[data-scene]").forEach(function (svg) {
      var s = SCENES[svg.getAttribute("data-scene")];
      if (s) draw(svg, s);
    });
  }
  window.draw385 = render;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", render); else render();
})();
