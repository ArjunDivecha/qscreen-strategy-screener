(function () {
  "use strict";

  var DATA = JSON.parse(document.getElementById("report-data").textContent);
  var SVGNS = "http://www.w3.org/2000/svg";

  var CAT_COLORS_HEX = {
    "Equities": "#1b8449", "Currencies": "#0a9a9a", "Bonds": "#235d99",
    "Cryptocurrencies": "#6a3fb0", "REITs": "#a32350", "Multi-Asset": "#c1502a",
    "Other": "#6b7a2e", "Commodities": "#a66e00"
  };

  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === "html") e.innerHTML = attrs[k];
      else if (k === "text") e.textContent = attrs[k];
      else e.setAttribute(k, attrs[k]);
    }
    if (children) children.forEach(function (c) { e.appendChild(c); });
    return e;
  }
  function svgEl(tag, attrs) {
    var e = document.createElementNS(SVGNS, tag);
    if (attrs) for (var k in attrs) e.setAttribute(k, attrs[k]);
    return e;
  }
  function slug(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, ""); }

  function fmtSigned(v, decimals) {
    if (v === null || v === undefined || isNaN(v)) return '<span class="dash">—</span>';
    decimals = decimals === undefined ? 2 : decimals;
    var cls = v > 0 ? "gain-text" : (v < 0 ? "loss-text" : "");
    var sign = v > 0 ? "+" : "";
    return '<span class="' + cls + '">' + sign + v.toFixed(decimals) + "%</span>";
  }
  function fmtPlain(v, suffix, decimals) {
    if (v === null || v === undefined || v === "" || isNaN(v)) return '<span class="dash">—</span>';
    decimals = decimals === undefined ? 2 : decimals;
    return (typeof v === "number" ? v.toFixed(decimals) : v) + (suffix || "");
  }
  function fmtText(v) {
    if (v === null || v === undefined || v === "") return '<span class="dash">—</span>';
    return v;
  }

  function percentile(arr, p) {
    var a = arr.slice().sort(function (x, y) { return x - y; });
    var idx = p * (a.length - 1);
    var lo = Math.floor(idx), hi = Math.ceil(idx);
    if (lo === hi) return a[lo];
    return a[lo] + (a[hi] - a[lo]) * (idx - lo);
  }
  function niceStep(range) {
    var raw = range / 5;
    var mag = Math.pow(10, Math.floor(Math.log10(raw)));
    var norm = raw / mag;
    var step = norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10;
    return step * mag;
  }

  /* ============================ Hero stats ============================ */
  function buildHeroStats() {
    var h = DATA.headline;
    var wrap = document.getElementById("hero-stats");
    var tiles = [
      { label: "Strategies audited", value: h.n_total, sub: h.n_no_oos_window + " with no OOS window" },
      { label: "Median paper claim", value: h.median_paper_claimed_pct.toFixed(1) + "%", sub: "annual return, as published" },
      { label: "Median true OOS CAGR", value: h.median_oos_cagr_pct.toFixed(2) + "%", sub: "years the paper never saw", cls: h.median_oos_cagr_pct >= 0 ? "gain" : "loss" },
      { label: "Survival rate", value: h.survival_rate_pct.toFixed(0) + "%", sub: "strategies with OOS CAGR > 0" }
    ];
    tiles.forEach(function (t) {
      wrap.appendChild(el("div", { class: "stat-tile" }, [
        el("div", { class: "label", text: t.label }),
        el("div", { class: "value" + (t.cls ? " " + t.cls : ""), text: t.value }),
        el("div", { class: "sub", text: t.sub })
      ]));
    });
  }

  /* ============================ Scatter chart ============================ */
  function buildScatter() {
    var data = DATA.scatter;
    var W = 560, H = 380, M = { top: 14, right: 18, bottom: 40, left: 46 };
    var plotW = W - M.left - M.right, plotH = H - M.top - M.bottom;

    var xs = data.map(function (d) { return d.paper_pct; });
    var ys = data.map(function (d) { return d.oos_cagr_pct; });
    var x0 = Math.min(0, percentile(xs, 0.02)), x1 = percentile(xs, 0.96);
    var y0 = percentile(ys, 0.02), y1 = percentile(ys, 0.98);
    y0 = Math.min(y0, -1); y1 = Math.max(y1, 1);
    var xPad = (x1 - x0) * 0.05, yPad = (y1 - y0) * 0.08;
    x0 -= xPad; x1 += xPad; y0 -= yPad; y1 += yPad;

    function sx(v) { return M.left + (clamp(v, x0, x1) - x0) / (x1 - x0) * plotW; }
    function sy(v) { return M.top + plotH - (clamp(v, y0, y1) - y0) / (y1 - y0) * plotH; }
    function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "Scatter of paper claimed return versus out of sample CAGR" });

    // Gridlines (y)
    var yStep = niceStep(y1 - y0);
    for (var gy = Math.ceil(y0 / yStep) * yStep; gy <= y1; gy += yStep) {
      svg.appendChild(svgEl("line", { class: "grid-line", x1: M.left, x2: W - M.right, y1: sy(gy), y2: sy(gy) }));
      var lbl = svgEl("text", { class: "axis-label", x: M.left - 6, y: sy(gy) + 3, "text-anchor": "end" });
      lbl.textContent = (gy > 0 ? "+" : "") + Math.round(gy) + "%";
      svg.appendChild(lbl);
    }
    var xStep = niceStep(x1 - x0);
    for (var gx = Math.ceil(x0 / xStep) * xStep; gx <= x1; gx += xStep) {
      var lblx = svgEl("text", { class: "axis-label", x: sx(gx), y: H - M.bottom + 16, "text-anchor": "middle" });
      lblx.textContent = (gx > 0 ? "+" : "") + Math.round(gx) + "%";
      svg.appendChild(lblx);
    }

    // Zero line (y=0)
    if (y0 < 0 && y1 > 0) svg.appendChild(svgEl("line", { class: "zero-line", x1: M.left, x2: W - M.right, y1: sy(0), y2: sy(0) }));

    // Reference diagonal: OOS CAGR == paper claim
    svg.appendChild(svgEl("line", { class: "ref-line", x1: sx(x0), x2: sx(x1), y1: sy(x0), y2: sy(x1) }));

    // Axis titles
    var xt = svgEl("text", { class: "axis-label", x: M.left + plotW / 2, y: H - 4, "text-anchor": "middle" });
    xt.textContent = "Paper's claimed annual return →";
    svg.appendChild(xt);
    var ytxt = svgEl("text", { class: "axis-label", x: -(M.top + plotH / 2), y: 12, "text-anchor": "middle", transform: "rotate(-90)" });
    ytxt.textContent = "True out-of-sample CAGR →";
    svg.appendChild(ytxt);

    // Points
    data.forEach(function (d) {
      var c = svgEl("circle", {
        class: "dot", cx: sx(d.paper_pct), cy: sy(d.oos_cagr_pct), r: 3.4,
        fill: CAT_COLORS_HEX[d.category] || "#8b958d"
      });
      var title = svgEl("title", {});
      title.textContent = d.name + " (" + d.category + ")\nPaper claim: " + d.paper_pct.toFixed(1) + "%\nOOS CAGR: " + d.oos_cagr_pct.toFixed(2) + "%";
      c.appendChild(title);
      svg.appendChild(c);
    });

    document.getElementById("scatter-chart").appendChild(svg);

    // Legend
    var legend = el("div", { class: "legend" });
    Object.keys(CAT_COLORS_HEX).forEach(function (cat) {
      if (!DATA.categories.some(function (c) { return c.summary.category === cat; })) return;
      legend.appendChild(el("span", { class: "item" }, [
        el("span", { class: "swatch", style: "background:" + CAT_COLORS_HEX[cat] }),
        el("span", { text: cat })
      ]));
    });
    document.getElementById("scatter-chart").parentElement.appendChild(legend);
  }

  /* ============================ Category bar chart ============================ */
  function buildCategoryBarChart() {
    var cats = DATA.categories.slice().sort(function (a, b) {
      var av = a.summary.median_oos_cagr_pct, bv = b.summary.median_oos_cagr_pct;
      return (bv === null ? -999 : bv) - (av === null ? -999 : av);
    });

    var W = 420, rowH = 34, top = 10, bottom = 30;
    var H = top + bottom + rowH * cats.length;
    var left = 118, right = 56;
    var plotW = W - left - right;

    var vals = cats.map(function (c) { return c.summary.median_oos_cagr_pct || 0; });
    var vMin = Math.min(0, Math.min.apply(null, vals));
    var vMax = Math.max(0, Math.max.apply(null, vals));
    var pad = (vMax - vMin) * 0.15 || 1;
    vMin -= pad; vMax += pad;

    function sx(v) { return left + (v - vMin) / (vMax - vMin) * plotW; }

    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": "Median out of sample CAGR by category" });

    var zeroX = sx(0);
    svg.appendChild(svgEl("line", { class: "zero-line", x1: zeroX, x2: zeroX, y1: top, y2: H - bottom + 4 }));

    var medAll = DATA.headline.median_oos_cagr_pct;
    var medX = sx(medAll);
    svg.appendChild(svgEl("line", { class: "ref-line", x1: medX, x2: medX, y1: top, y2: H - bottom + 4 }));

    cats.forEach(function (c, i) {
      var y = top + i * rowH;
      var v = c.summary.median_oos_cagr_pct || 0;
      var barX = Math.min(sx(0), sx(v));
      var barW = Math.abs(sx(v) - sx(0));
      var color = CAT_COLORS_HEX[c.summary.category] || "#8b958d";

      var lbl = svgEl("text", { class: "bar-label", x: left - 8, y: y + rowH / 2 - 5, "text-anchor": "end" });
      lbl.textContent = c.summary.category;
      svg.appendChild(lbl);
      var sub = svgEl("text", { class: "axis-label", x: left - 8, y: y + rowH / 2 + 8, "text-anchor": "end" });
      sub.textContent = "n=" + c.summary.n_strategies;
      svg.appendChild(sub);

      svg.appendChild(svgEl("rect", {
        x: barX, y: y + 5, width: Math.max(barW, 1.5), height: rowH - 14,
        fill: color, opacity: 0.88
      }));

      // Negative labels sit just right of the zero line (not left of the bar
      // tip) so short bars near zero never crowd the row-name column.
      var valLabel = svgEl("text", {
        class: "bar-value", y: y + rowH / 2 + 3,
        x: v >= 0 ? sx(v) + 6 : zeroX + 6,
        "text-anchor": "start",
        fill: v >= 0 ? "#0b7a2e" : "#b23030"
      });
      valLabel.textContent = (v > 0 ? "+" : "") + v.toFixed(2) + "%";
      svg.appendChild(valLabel);
    });

    var medLbl = svgEl("text", { class: "axis-label", x: medX, y: H - bottom + 18, "text-anchor": "middle" });
    medLbl.textContent = "corpus median";
    svg.appendChild(medLbl);
    var zeroLbl = svgEl("text", { class: "axis-label", x: zeroX, y: top - 2, "text-anchor": "middle" });
    zeroLbl.textContent = "0%";
    svg.appendChild(zeroLbl);

    document.getElementById("category-bar-chart").appendChild(svg);
  }

  /* ============================ Category nav ============================ */
  function buildCatNav(orderedCats) {
    var nav = document.getElementById("cat-nav");
    orderedCats.forEach(function (c) {
      var s = c.summary;
      var a = el("a", { href: "#cat-" + slug(s.category) }, [
        el("span", { class: "dot", style: "background:" + CAT_COLORS_HEX[s.category] }),
        el("span", { text: s.category + " (" + s.n_strategies + ")" })
      ]);
      nav.appendChild(a);
    });
  }

  /* ============================ Category sections ============================ */
  var ROWS_SHOWN_DEFAULT = 20;

  var COLUMNS = [
    { key: "rank", label: "#", type: "num", sortable: false },
    { key: "name", label: "Strategy", type: "text", sortable: true },
    { key: "paper_indicative_perf_val", label: "Paper Claim", type: "num", sortable: true },
    { key: "paper_sharpe_val", label: "Paper Sharpe", type: "num", sortable: true },
    { key: "oos_years", label: "OOS Yrs", type: "num", sortable: true },
    { key: "oos_total_return_pct", label: "OOS Return", type: "num", sortable: true },
    { key: "oos_cagr_pct", label: "OOS CAGR", type: "num", sortable: true },
    { key: "oos_1y_return_pct", label: "1Y", type: "num", sortable: true },
    { key: "oos_3y_cagr_pct", label: "3Y Ann.", type: "num", sortable: true },
    { key: "oos_5y_cagr_pct", label: "5Y Ann.", type: "num", sortable: true },
    { key: "oos_max_drawdown_pct", label: "OOS Max DD", type: "num", sortable: true },
    { key: "note_col", label: "Note", type: "text", sortable: false }
  ];

  function prepRow(r, i) {
    var paperVal = parseFloat(String(r.paper_indicative_perf).replace("%", ""));
    var sharpeVal = parseFloat(r.paper_sharpe);
    return Object.assign({}, r, {
      rank: i + 1,
      paper_indicative_perf_val: isNaN(paperVal) ? null : paperVal,
      paper_sharpe_val: isNaN(sharpeVal) ? null : sharpeVal,
      note_col: r.oos_note || ""
    });
  }

  function renderTableRows(tbody, rows) {
    tbody.innerHTML = "";
    rows.forEach(function (r, i) {
      var tr = el("tr", {});
      if (i >= ROWS_SHOWN_DEFAULT) tr.className = "hidden-row";

      tr.appendChild(el("td", { class: "num" }, [el("span", { class: "rank-badge", text: String(i + 1) })]));

      var nameTd = el("td", { class: "name" });
      var link = el("a", { href: r.url || "#", target: "_blank", rel: "noopener", text: r.display_name });
      nameTd.appendChild(link);
      if (r.paper_period) nameTd.appendChild(el("span", { class: "meta", text: r.paper_period + " · " + (r.paper_complexity || "") }));
      tr.appendChild(nameTd);

      tr.appendChild(el("td", { class: "num", html: fmtPlain(r.paper_indicative_perf_val, "%", 2) }));
      tr.appendChild(el("td", { class: "num", html: fmtPlain(r.paper_sharpe_val, "", 2) }));
      tr.appendChild(el("td", { class: "num", html: fmtPlain(r.oos_years, "y", 1) }));
      tr.appendChild(el("td", { class: "num", html: fmtSigned(r.oos_total_return_pct, 2) }));
      tr.appendChild(el("td", { class: "num", html: fmtSigned(r.oos_cagr_pct, 2) }));
      tr.appendChild(el("td", { class: "num", html: fmtSigned(r.oos_1y_return_pct, 2) }));
      tr.appendChild(el("td", { class: "num", html: fmtSigned(r.oos_3y_cagr_pct, 2) }));
      tr.appendChild(el("td", { class: "num", html: fmtSigned(r.oos_5y_cagr_pct, 2) }));
      tr.appendChild(el("td", { class: "num", html: fmtSigned(r.oos_max_drawdown_pct, 2) }));
      tr.appendChild(el("td", { html: r.note_col ? '<span class="note-text">' + r.note_col + "</span>" : '<span class="dash">—</span>' }));

      tbody.appendChild(tr);
    });
  }

  function buildCategorySection(catBlock) {
    var s = catBlock.summary;
    var rows = catBlock.strategies.map(prepRow);
    var color = CAT_COLORS_HEX[s.category] || "#8b958d";

    var section = el("section", { class: "cat-section", id: "cat-" + slug(s.category) });

    var header = el("div", { class: "cat-header" }, [
      el("div", { class: "cat-name-wrap" }, [
        el("span", { class: "cat-dot", style: "background:" + color }),
        el("h3", { text: s.category })
      ]),
      el("div", { class: "cat-stats" }, [
        el("span", {}, [document.createTextNode("n = "), el("b", { text: String(s.n_strategies) })]),
        el("span", {}, [document.createTextNode("median OOS CAGR "), el("b", { html: fmtSigned(s.median_oos_cagr_pct, 2) })]),
        el("span", {}, [document.createTextNode("survival "), el("b", { text: (s.survival_rate_pct !== null ? s.survival_rate_pct.toFixed(0) : "—") + "%" })])
      ])
    ]);
    section.appendChild(header);

    // Highlight strip: best performer with a chart, if we have one embedded
    var best = rows[0];
    if (best && DATA.highlight_charts[best.name]) {
      var strip = el("div", { class: "highlight-strip" }, [
        el("img", { src: DATA.highlight_charts[best.name], alt: "Equity curve for " + best.display_name }),
        el("div", { class: "hl-body" }, [
          el("div", { class: "hl-tag", text: "Category leader" }),
          el("div", { class: "hl-name", text: best.display_name }),
          el("div", { class: "hl-figs" }, [
            el("span", { html: "Paper claim " + fmtPlain(best.paper_indicative_perf_val, "%") }),
            el("span", { html: "OOS CAGR " + fmtSigned(best.oos_cagr_pct) }),
            el("span", { html: "OOS window " + fmtPlain(best.oos_years, "y", 1) })
          ])
        ])
      ]);
      section.appendChild(strip);
    }

    // Table
    var tableWrap = el("div", { class: "table-wrap" });
    var table = el("table", { class: "strat-table" });
    var thead = el("thead", {});
    var headRow = el("tr", {});
    var sortState = { key: "oos_cagr_pct", dir: -1 };

    COLUMNS.forEach(function (col) {
      var th = el("th", { class: col.type === "num" ? "num" : "" });
      th.textContent = col.label;
      if (col.sortable) {
        var arrow = el("span", { class: "arrow", text: "▼" });
        th.appendChild(arrow);
        if (col.key === sortState.key) th.classList.add("sorted");
        th.addEventListener("click", function () {
          if (sortState.key === col.key) sortState.dir *= -1;
          else { sortState.key = col.key; sortState.dir = -1; }
          Array.prototype.forEach.call(headRow.children, function (h) {
            h.classList.remove("sorted");
            var a = h.querySelector(".arrow");
            if (a) a.textContent = "▼";
          });
          th.classList.add("sorted");
          arrow.textContent = sortState.dir === -1 ? "▼" : "▲";
          sortRows();
        });
      }
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    var tbody = el("tbody", {});
    table.appendChild(tbody);
    tableWrap.appendChild(table);
    section.appendChild(tableWrap);

    function sortRows() {
      var sorted = rows.slice().sort(function (a, b) {
        var av = a[sortState.key], bv = b[sortState.key];
        var aNull = av === null || av === undefined || av === "";
        var bNull = bv === null || bv === undefined || bv === "";
        if (aNull && bNull) return 0;
        if (aNull) return 1;
        if (bNull) return -1;
        if (typeof av === "string") return sortState.dir === 1 ? av.localeCompare(bv) : bv.localeCompare(av);
        return sortState.dir === 1 ? (av - bv) : (bv - av);
      });
      renderTableRows(tbody, sorted);
    }
    sortRows();

    // Expand/collapse footer
    if (rows.length > ROWS_SHOWN_DEFAULT) {
      var footerRow = el("div", { class: "table-footer" }, [
        el("span", { text: "Showing top " + ROWS_SHOWN_DEFAULT + " of " + rows.length + ", sorted by out-of-sample CAGR." })
      ]);
      var btn = el("button", { class: "expand-btn", text: "Show all " + rows.length });
      var expanded = false;
      btn.addEventListener("click", function () {
        expanded = !expanded;
        Array.prototype.forEach.call(tbody.querySelectorAll("tr"), function (tr, i) {
          if (i >= ROWS_SHOWN_DEFAULT) tr.classList.toggle("hidden-row", !expanded);
        });
        btn.textContent = expanded ? "Show fewer" : "Show all " + rows.length;
      });
      footerRow.appendChild(btn);
      section.appendChild(footerRow);
    }

    return section;
  }

  function buildCategorySections() {
    var container = document.getElementById("categories-container");
    var ordered = DATA.categories.slice().sort(function (a, b) {
      var av = a.summary.median_oos_cagr_pct, bv = b.summary.median_oos_cagr_pct;
      return (bv === null ? -999 : bv) - (av === null ? -999 : av);
    });
    buildCatNav(ordered);
    ordered.forEach(function (catBlock) {
      container.appendChild(buildCategorySection(catBlock));
    });
  }

  /* ============================ Footnotes ============================ */
  function buildFootnotes() {
    var list = document.getElementById("footnote-list");
    var h = DATA.headline;
    var notes = [
      h.n_no_oos_window + " of " + h.n_total + " strategies have no true out-of-sample window " +
        "because the paper's own study period runs up to (or past) the last date QuantConnect's " +
        "backtest reached; these are listed at the bottom of their category, unscored rather than guessed.",
      "“OOS CAGR” is the annualized return of QuantConnect's daily equity curve from January 1 " +
        "after the paper's study period ended through the last available backtest date. Windows shorter " +
        "than 6 months show total return only — too little data to annualize responsibly.",
      "“1Y”, “3Y Ann.” and “5Y Ann.” are trailing returns measured from the OOS start date — 1Y is a " +
        "simple total return, 3Y and 5Y are annualized (fund fact-sheet style). A horizon is left blank " +
        "whenever the OOS window doesn't reach that far yet, never estimated or extrapolated.",
      "“Multi-Asset” groups strategies whose Markets Traded field lists more than one asset class " +
        "(e.g. bonds, commodities, currencies and equities together).",
      "A small number of QuantConnect's own chart thumbnails render as solid blank images — a rendering " +
        "artifact on QuantConnect's CDN, confirmed unrelated to the underlying equity-curve data used for " +
        "every calculation in this ledger.",
      "Paper-reported Sharpe ratios and returns are taken at face value from Quantpedia's strategy pages " +
        "and are not independently verified; only the out-of-sample figures are computed directly from " +
        "QuantConnect's own simulated daily equity curve."
    ];
    notes.forEach(function (n) { list.appendChild(el("li", { text: n })); });

    document.getElementById("provenance").innerHTML =
      '<h4 style="margin-top:1.5rem;">Source data</h4>' +
      '<p>Full per-strategy dataset (800 rows, 78 columns, including trailing 1/3/5-year OOS figures): <code>qc_extracted_data/strategies_master.xlsx</code></p>' +
      '<p>Extraction pipeline: <code>extract_qc_strategy_data.py</code> &middot; Report data pipeline: <code>build_oos_report_data.py</code></p>';
  }

  buildHeroStats();
  buildScatter();
  buildCategoryBarChart();
  buildCategorySections();
  buildFootnotes();
})();
