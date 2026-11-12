/* The one figure engine of the booklet. Every drawing on every page is declared in its HTML and drawn
   here to scale, in the book's colours:
     <svg data-fig='{"x":[-5,5],"y":[-5,5],"grid":true,"polys":[{"pts":[[0,1],[0,4],[4,2.7]]}]}'></svg>
   Answer choices name a shared base from window.FIG_BASES and the operation applied to it, so every
   image is computed, never redrawn by eye: {"use":"q2","ops":["rot180"]}. A base holds pts, inner and
   a frame (the keys below); a base with only a frame is a whole figure used as it is.

   Keys: u (mm per unit), pad (mm), x, y (ranges), grid, numbers, axes ("solid" or "dash"),
   axisNames, polys, segs, points, arrows, arcs, lines, vlines, hlines, grow. numbers may be {x:[a,b],y:[c,d],step:n}:
   the numbered part of a longer axis, every n-th unit. pointAt: [dx,dy] moves the label of a shared
   base's point in one choice. grow: inside a .plane frame, add whole units above and below until the
   plane fills the frame's height (the frame first takes the plane's own size).
   vlines / hlines: [{at, label}] dashed lines x=at / y=at across the whole plane (mirror lines).
   Arc keys: c, r, from, to, head (false = no arrowhead).
   Poly keys: pts or base, ops, about, shift, fill, line, width, open, inner (segments moved with it),
   names (vertex labels, set outside the shape with a dot on each vertex), label ({at, t, rot}).
   Point keys: at, t, dx, dy, dot (false = label only), color, size.
   style: "original" (blue) or "image" (orange) gives a poly the book's colours; fill, line and width
   still override it. Without a style a poly is grey, as the curriculum pages need. */
(function () {
  var NS = 'http://www.w3.org/2000/svg';
  var INK = '#0b3a75', GRID = '#c9d6e2', MM = 96 / 25.4;
  var OPS = {
    same: function (p) { return p; },
    rot90cw: function (p) { return [p[1], -p[0]]; },
    rot90ccw: function (p) { return [-p[1], p[0]]; },
    rot180: function (p) { return [-p[0], -p[1]]; },
    flipX: function (p) { return [p[0], -p[1]]; },
    flipY: function (p) { return [-p[0], p[1]]; }
  };

  var STYLES = {
    original: { fill: '#dbe9f7', line: INK, width: .6 },
    image: { fill: '#fde8d3', line: '#b45f06', width: .6 }
  };

  function move(points, poly) {
    var c = poly.about || [0, 0], s = poly.shift || [0, 0];
    return points.map(function (p) {
      var q = [p[0] - c[0], p[1] - c[1]];
      (poly.ops || []).forEach(function (name) { q = OPS[name](q); });
      return [q[0] + c[0] + s[0], q[1] + c[1] + s[1]];
    });
  }

  function grow(svg, f) {
    var frame = svg.parentElement, u = f.u || 6, pad = f.pad === undefined ? 5 : f.pad;
    if (!f.grow || !frame || !frame.classList.contains('plane') || !frame.dataset.sized) return f;
    var room = Math.floor((frame.getBoundingClientRect().height / MM - 2 * pad) / u + 1e-6);
    var extra = Math.max(0, room - (f.y[1] - f.y[0]));
    return Object.assign({}, f, { y: [f.y[0] - Math.ceil(extra / 2), f.y[1] + Math.floor(extra / 2)] });
  }

  function draw(svg, f, bases) {
    f = grow(svg, f);
    var u = f.u || 6, pad = f.pad === undefined ? 5 : f.pad;
    var X = function (x) { return (x - f.x[0]) * u + pad; };
    var Y = function (y) { return (f.y[1] - y) * u + pad; };
    var w = (f.x[1] - f.x[0]) * u + 2 * pad, h = (f.y[1] - f.y[0]) * u + 2 * pad;
    svg.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
    svg.setAttribute('width', w + 'mm');
    svg.setAttribute('height', h + 'mm');
    svg.setAttribute('direction', 'ltr');
    if (svg.dataset.caption) { svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', svg.dataset.caption); }

    function add(tag, attrs, text) {
      var e = document.createElementNS(NS, tag);
      Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
      if (text !== undefined) e.textContent = text;
      svg.appendChild(e);
      return e;
    }
    function line(a, b, attrs) {
      return add('line', Object.assign({ x1: X(a[0]), y1: Y(a[1]), x2: X(b[0]), y2: Y(b[1]), stroke: INK, 'stroke-width': .35 }, attrs || {}));
    }
    function text(at, t, o) {
      o = o || {};
      var x = X(at[0]) + (o.dx || 0), y = Y(at[1]) + (o.dy || 0);
      var a = { x: x, y: y, 'font-size': o.size || 3.5, 'font-family': 'Arial,"Noto Sans Hebrew",sans-serif', 'font-weight': o.weight || 700,
        fill: o.color || INK, 'text-anchor': 'middle', 'dominant-baseline': 'central', stroke: '#fff', 'stroke-width': o.halo === 0 ? 0 : .7, 'paint-order': 'stroke' };
      if (o.rot) a.transform = 'rotate(' + o.rot + ' ' + x + ' ' + y + ')';
      if (o.rtl) a.direction = 'rtl';
      return add('text', a, t);
    }
    function head(tip, from, color) {
      var dx = tip[0] - from[0], dy = tip[1] - from[1], l = Math.hypot(dx, dy) || 1, s = 1.7;
      dx /= l; dy /= l;
      add('polygon', { fill: color || INK, points: [[tip[0], tip[1]], [tip[0] - s * dx - .62 * s * dy, tip[1] - s * dy + .62 * s * dx], [tip[0] - s * dx + .62 * s * dy, tip[1] - s * dy - .62 * s * dx]].map(function (p) { return p.join(','); }).join(' ') });
    }

    if (f.grid) {
      for (var gx = Math.ceil(f.x[0]); gx <= f.x[1]; gx++) line([gx, f.y[0]], [gx, f.y[1]], { stroke: GRID, 'stroke-width': .2 });
      for (var gy = Math.ceil(f.y[0]); gy <= f.y[1]; gy++) line([f.x[0], gy], [f.x[1], gy], { stroke: GRID, 'stroke-width': .2 });
    }
    (f.lines || []).forEach(function (l) {
      line(l[0], l[1], { 'stroke-dasharray': '1.8 1.2', 'stroke-width': .45, stroke: '#27384a' });
    });
    (f.vlines || []).forEach(function (v) {
      line([v.at, f.y[0]], [v.at, f.y[1]], { 'stroke-dasharray': '1.8 1.2', 'stroke-width': .5, stroke: '#27384a' });
      if (v.label) text([v.at, f.y[1]], v.label, { dx: 1.2 + v.label.length * 1.1, dy: 2.2, size: 3.2 });
    });
    (f.hlines || []).forEach(function (v) {
      line([f.x[0], v.at], [f.x[1], v.at], { 'stroke-dasharray': '1.8 1.2', 'stroke-width': .5, stroke: '#27384a' });
      if (v.label) text([f.x[0], v.at], v.label, { dx: 1.2 + v.label.length * 1.1, dy: -2.2, size: 3.2 });
    });
    (f.polys || []).forEach(function (poly) {
      poly = Object.assign({}, STYLES[poly.style], poly);
      var pts = move(poly.pts || bases[poly.base].pts, poly);
      add(poly.open ? 'polyline' : 'polygon', {
        points: pts.map(function (p) { return X(p[0]) + ',' + Y(p[1]); }).join(' '),
        fill: poly.open ? 'none' : poly.fill === undefined ? '#b4bcc4' : poly.fill, stroke: poly.line || '#27384a',
        'stroke-width': poly.width || .4, 'stroke-linejoin': 'round', 'fill-opacity': poly.opacity || 1
      });
      var inner = poly.inner || (poly.base && bases[poly.base].inner) || [];
      inner.forEach(function (s) { var q = move(s, poly); line(q[0], q[1], { stroke: poly.line || '#27384a', 'stroke-width': .4 }); });
      if (poly.label) {
        var cx = poly.label.at || pts.reduce(function (a, p) { return [a[0] + p[0] / pts.length, a[1] + p[1] / pts.length]; }, [0, 0]);
        text(cx, poly.label.t, { rot: poly.label.rot, size: 4.2, halo: 0, color: '#10202e', rtl: true });
      }
      if (poly.names) {
        var mid = pts.reduce(function (a, p) { return [a[0] + p[0] / pts.length, a[1] + p[1] / pts.length]; }, [0, 0]);
        pts.forEach(function (p, i) {
          var dx = p[0] - mid[0], dy = p[1] - mid[1], l = Math.hypot(dx, dy) || 1;
          add('circle', { cx: X(p[0]), cy: Y(p[1]), r: .75, fill: poly.line || INK });
          text(p, poly.names[i] || '', { dx: 2.8 * dx / l, dy: -2.8 * dy / l, color: poly.line || INK });
        });
      }
    });
    if (f.axes) {
      var dash = f.axes === 'dash' ? { 'stroke-dasharray': '1.4 1.1' } : {};
      var ax = Object.assign({ stroke: f.axes === 'dash' ? '#51606e' : INK, 'stroke-width': f.axes === 'dash' ? .3 : .45 }, dash);
      var ox = f.ox || 0, oy = f.oy || 0;
      line([f.x[0], oy], [f.x[1], oy], ax);
      line([ox, f.y[0]], [ox, f.y[1]], ax);
      if (f.arrowheads !== false) {
        head([X(f.x[1]) + 2, Y(oy)], [X(f.x[1]), Y(oy)], ax.stroke);
        head([X(ox), Y(f.y[1]) - 2], [X(ox), Y(f.y[1])], ax.stroke);
      }
      if (f.numbers) {
        var nx = f.numbers.x || f.x, ny = f.numbers.y || f.y, step = f.numbers.step || 1;
        for (var n = Math.ceil(nx[0] / step) * step; n <= nx[1]; n += step) if (n) text([n, oy], String(n).replace('-', '−'), { dy: 2.6, size: 2.5, weight: 400, color: '#27384a' });
        for (var m = Math.ceil(ny[0] / step) * step; m <= ny[1]; m += step) if (m) text([ox, m], String(m).replace('-', '−'), { dx: -2.6, size: 2.5, weight: 400, color: '#27384a' });
      }
      if (f.axisNames) {
        text([f.x[1], oy], 'x', { dx: 3.2, dy: -2.2, size: 3.2 });
        text([ox, f.y[1]], 'y', { dx: 2.6, dy: -2.4, size: 3.2 });
      }
    }
    (f.segs || []).forEach(function (s) { line(s[0], s[1], { stroke: '#27384a', 'stroke-width': .4 }); });
    (f.arrows || []).forEach(function (a) {
      line(a[0], a[1], { stroke: '#7b8794', 'stroke-width': .5 });
      head([X(a[1][0]), Y(a[1][1])], [X(a[0][0]), Y(a[0][1])], '#7b8794');
    });
    (f.arcs || []).forEach(function (a) {
      var rad = function (d) { return d * Math.PI / 180; };
      var S = [X(a.c[0] + a.r * Math.cos(rad(a.from))), Y(a.c[1] + a.r * Math.sin(rad(a.from)))];
      var E = [X(a.c[0] + a.r * Math.cos(rad(a.to))), Y(a.c[1] + a.r * Math.sin(rad(a.to)))];
      add('path', { d: 'M' + S + ' A' + a.r * u + ',' + a.r * u + ' 0 0 1 ' + E, fill: 'none', stroke: '#7b8794', 'stroke-width': .5 });
      var back = rad(a.to + 18);
      if (a.head !== false) head(E, [X(a.c[0] + a.r * Math.cos(back)), Y(a.c[1] + a.r * Math.sin(back))], '#7b8794');
    });
    (f.points || []).forEach(function (p) {
      if (p.dot !== false) add('circle', { cx: X(p.at[0]), cy: Y(p.at[1]), r: .75, fill: p.color || '#10202e' });
      if (p.t) text(p.at, p.t, { dx: p.dx === undefined ? 2.8 : p.dx, dy: p.dy === undefined ? -2.6 : p.dy, color: p.color || '#10202e', size: p.size });
    });
  }

  /* Answer squares: whole 5 mm cells only, so no cell is cut at the edge. An empty .work is an answer
     box; a .work that holds a plane and a table is a layout row of the original worksheets. */
  function snap() {
    var cell = 5 * MM;
    document.querySelectorAll('.work:empty').forEach(function (b) {
      b.style.height = ''; b.style.flex = '';
      var h = b.getBoundingClientRect().height;
      b.style.flex = 'none';
      b.style.height = Math.floor(h / cell) * cell + 'px';
    });
  }

  function run() {
    var bases = window.FIG_BASES || {};
    document.querySelectorAll('svg[data-fig]').forEach(function (svg) {
      svg.textContent = '';
      var f = JSON.parse(svg.getAttribute('data-fig')), base = bases[f.use];
      if (base) {
        var one = base.pts ? [{ base: f.use, ops: f.ops, shift: f.shift }] : base.frame.polys;
        f = Object.assign({}, base.frame, f, { polys: one });
        if (f.pointAt) f.points = f.points.map(function (q) { return Object.assign({}, q, { dx: f.pointAt[0], dy: f.pointAt[1] }); });
      }
      draw(svg, f, bases);
      var frame = svg.parentElement;
      if (f.grow && frame && frame.classList.contains('plane') && !frame.dataset.sized) {
        frame.style.width = svg.getAttribute('width'); frame.style.minHeight = svg.getAttribute('height');
        frame.dataset.sized = '1';
      }
    });
    snap();
  }
  window.drawFigures = run;
  window.drawPlanes = run;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
  window.addEventListener('load', snap);
  window.addEventListener('beforeprint', snap);
})();
