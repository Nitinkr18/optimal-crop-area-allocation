// Solves both LPs for the chosen state and season and fills the pages. Pages switch by URL hash.
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const DEF = { land_pct: 100, target_pct: 100, bounds: "historical", band_pct: 20, pulse_share: 0, yield_method: "mean" };
const S = { seasons: {}, blocked: {}, trace: {}, r: null, india: {}, geo: null, model: 1, last: null, crop: null, cropData: {}, set: { ...DEF }, base: {} };
const isDefault = (st) => Object.keys(DEF).every((k) => st[k] === DEF[k]);
const indiaKey = (season) => `${season}|${JSON.stringify(S.set)}`;
const INK = "#111", ACC = "#2f6f4e", ACC_L = "#9fc5ad", GREY = "#c9c9c9", MUTED = "#8a8a8a";
const SOIL = "#8a5a22";                                   // Model 2 (land) colour; Model 1 (output) is ACC
const MODEL_COL = (m) => (m === 2 ? SOIL : ACC);
const SCALE = [[0, "#eef5f0"], [0.5, "#7fae90"], [1, "#1d4d34"]];
const SCALE2 = [[0, "#f7efe4"], [0.5, "#c69a63"], [1, "#5e3b12"]];        // Model 2 (land) maps
const SOIL_L = "#dcc3a0";
const TREND = ["#1d4d34", "#2f6f4e", "#5f9676", "#9fc5ad", "#8a8a8a"];
const FONT = getComputedStyle(document.body).fontFamily;
const PAGES = $$(".page").map((p) => p.id);
const NAMES = Object.fromEntries($$(".menu a").map((a) => [a.getAttribute("href").slice(1), a.textContent.trim()]));

const fmt = (x, d = 0) => (x == null ? "–" : Number(x).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }));
const big = (x) => (x == null ? "–" : x >= 1e6 ? fmt(x / 1e6, 2) + " M" : x >= 1e3 ? fmt(x / 1e3, 1) + " k" : fmt(x));
const pct = (x, d = 1) => (x == null ? "–" : (x > 0 ? "+" : x < 0 ? "−" : "") + fmt(Math.abs(x), d) + "%");
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const title = (s) => String(s).toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
const list = (a) => (a.length <= 1 ? a.join("") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1]);

$$("[data-ic]").forEach((el) => el.insertAdjacentHTML("afterbegin", icon(el.dataset.ic, el.classList.contains("brand-ic") ? 20 : 17)));

function status(msg, err = false) { const el = $("#status"); el.textContent = msg; el.className = "status" + (err ? " err" : ""); }

async function api(path, body) {
  const r = await fetch(path, body ? { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } } : {});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `Request failed (${r.status})`);
  return j;
}

// KPI tiles. A number moves from the value shown last time to the new one, so a re-solve shows which way it went;
// a tile whose value changed under new inputs (same state and season) flashes once. `m` colours the tile by model.
const PREV = {};
function kpis(sel, items, scope = "") {
  $(sel).innerHTML = items.map(([k, v, s, good, m]) =>
    `<div class="kpi${m ? " m" + m : ""}"><div class="k">${k}</div><div class="v${good ? " up" : ""}">${typeof v === "object" ? v.f(PREV[`${sel}|${scope}|${k}`] ?? 0) : v}</div>${s ? `<div class="s">${s}</div>` : ""}</div>`).join("");
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  items.forEach(([k, v], i) => {
    if (typeof v !== "object" || v.n == null) return;
    const key = `${sel}|${scope}|${k}`, seen = key in PREV, from = PREV[key] ?? 0, to = v.n, tile = $(sel).children[i], el = tile.querySelector(".v");
    PREV[key] = to;
    if (S.flash && seen && Math.abs(to - from) > 1e-9 * Math.max(1, Math.abs(to))) tile.classList.add("changed");
    if (still) { el.textContent = v.f(to); return; }
    const t0 = performance.now();
    const step = (t) => { const p = Math.min(1, (t - t0) / 600), e = 1 - (1 - p) ** 3; el.textContent = v.f(from + (to - from) * e); if (p < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  });
}
const N = (n, f) => ({ n, f });

function table(cols, rows) {
  const cls = (c) => [c.r ? "r" : "", c.cls || ""].join(" ").trim();
  return `<table><thead><tr>${cols.map((c) => `<th class="${cls(c)}">${c.label}</th>`).join("")}</tr></thead><tbody>${
    rows.map((row) => `<tr>${cols.map((c) => `<td class="${cls(c)}">${c.f ? c.f(row[c.k], row) : esc(row[c.k] ?? "–")}</td>`).join("")}</tr>`).join("")
  }</tbody></table>`;
}

function plot(sel, data, layout = {}, height = 340) {
  const { xaxis = {}, yaxis = {}, ...rest } = layout;
  for (const ax of [xaxis, yaxis]) if (typeof ax.title === "string") ax.title = { text: ax.title, font: { size: 12, color: MUTED } };
  return Plotly.react($(sel), data, {
    height, margin: { l: 60, r: 16, t: 8, b: 48 }, font: { family: FONT, size: 12, color: "#2b2b2b" },
    paper_bgcolor: "#fff", plot_bgcolor: "#fff", legend: { orientation: "h", y: 1.12, x: 0 }, bargap: 0.25,
    xaxis: { fixedrange: true, gridcolor: "#eee", zeroline: false, automargin: true, ...xaxis },
    yaxis: { fixedrange: true, gridcolor: "#eee", zeroline: false, automargin: true, ...yaxis },
    transition: { duration: 450, easing: "cubic-in-out" },
    ...rest,
  }, { displayModeBar: false, responsive: true });
}

// choropleth: one base layer (no data), the values, and an outline for the highlighted area.
// Each map remembers what it shows; a redraw (new inputs, other model, other crop) fades every area from its old
// value and colour scale to the new one, so you can see which states or districts moved and by how much.
const MAPS = {};
const rgb = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
const mix = (a, b, t) => "#" + rgb(a).map((v, i) => Math.round(v + (rgb(b)[i] - v) * t).toString(16).padStart(2, "0")).join("");
// values below 0 (worse than history) are grey, 0 is the palest colour, so a loss never reads as a small gain
const ramp = (base, zmin, zmax) => {
  const f = zmin < 0 ? -zmin / (zmax - zmin) : 0;
  return [[0, zmin < 0 ? GREY : base[0][1]], [f, base[0][1]], [f + (1 - f) / 2, base[1][1]], [1, base[2][1]]];
};
function map(sel, geo, ids, z, hover, { pick = null, height = 460, onClick = null, suffix = "%", label = "gain", scale = SCALE } = {}) {
  const el = $(sel), all = geo.features.map((f) => f.id), prev = MAPS[sel];
  const to = { z, zmin: Math.min(0, ...z), zmax: Math.max(...z, 1e-9) };
  to.scale = ramp(scale, to.zmin, to.zmax);
  const from = prev ? { z: ids.map((id) => prev.z[id] ?? prev.zmin), zmin: prev.zmin, zmax: prev.zmax, scale: prev.scale }
    : { z: ids.map(() => to.zmin), zmin: to.zmin, zmax: to.zmax, scale: to.scale };   // first draw fills in from blank
  const at = (e) => ({ z: from.z.map((v, i) => v + (to.z[i] - v) * e), zmin: from.zmin + (to.zmin - from.zmin) * e,
    zmax: from.zmax + (to.zmax - from.zmax) * e,
    scale: to.scale.map(([s, c], i) => [from.scale[i][0] + (s - from.scale[i][0]) * e, mix(from.scale[i][1], c, e)]) });
  const token = {}, keep = (f) => (MAPS[sel] = { token, z: Object.fromEntries(ids.map((id, i) => [id, f.z[i]])), zmin: f.zmin, zmax: f.zmax, scale: f.scale });
  const traces = [
    { type: "choropleth", geojson: geo, locations: all, z: all.map(() => 0), colorscale: [[0, "#f1f1f0"], [1, "#f1f1f0"]],
      showscale: false, marker: { line: { color: "#fff", width: 0.6 } }, hoverinfo: "skip" },
    { type: "choropleth", geojson: geo, locations: ids, z: from.z, colorscale: from.scale, zmin: from.zmin, zmax: from.zmax,
      marker: { line: { color: "#fff", width: 0.6 } }, text: hover, hovertemplate: "%{text}<extra></extra>",
      colorbar: { thickness: 10, len: 0.6, ticksuffix: suffix, outlinewidth: 0, title: { text: label, side: "top", font: { size: 11 } } } },
  ];
  if (pick) traces.push({ type: "choropleth", geojson: geo, locations: [pick], z: [1], showscale: false, hoverinfo: "skip",
    colorscale: [[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], marker: { line: { color: INK, width: 2.4 } } });
  Plotly.react($(sel), traces, {
    height, margin: { l: 0, r: 0, t: 0, b: 0 }, font: { family: FONT, size: 12 }, paper_bgcolor: "#fff",
    geo: { fitbounds: "locations", visible: false, projection: { type: "mercator" }, bgcolor: "#fff" }, dragmode: false,
  }, { displayModeBar: false, responsive: true, scrollZoom: false });
  if (onClick) { el.removeAllListeners?.("plotly_click"); el.on("plotly_click", (e) => onClick(e.points[0].location)); }
  keep(from);
  const same = from.z.every((v, i) => Math.abs(v - to.z[i]) < 1e-9) && from.scale.every(([s, c], i) => s === to.scale[i][0] && c === to.scale[i][1]);
  const apply = (f) => { keep(f); return Plotly.restyle(el, { z: [f.z], zmin: [f.zmin], zmax: [f.zmax], colorscale: [f.scale] }, [1]); };
  if (same) return;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return apply(at(1));
  const t0 = performance.now();
  const step = async () => {
    if (MAPS[sel].token !== token) return;                     // a newer draw took over
    const p = Math.min(1, (performance.now() - t0) / 800);
    await apply(at(1 - (1 - p) ** 3));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ------------------------------------------------------------------ navigation
function show(hash = location.hash) {
  const page = PAGES.includes(hash.slice(1)) ? hash.slice(1) : "overview";
  $$(".page").forEach((p) => p.classList.toggle("on", p.id === page));
  $$(".menu a").forEach((a) => a.classList.toggle("on", a.getAttribute("href") === "#" + page));
  const i = PAGES.indexOf(page);
  for (const [id, j] of [["prev", i - 1], ["next", i + 1]]) {
    const b = $("#" + id), p = PAGES[j];
    b.classList.toggle("hidden", !p);
    if (p) { b.href = "#" + p; b.querySelector(".t").textContent = NAMES[p]; }
  }
  window.scrollTo(0, 0);
  draw(page);
}
window.addEventListener("hashchange", () => show());
// A link like /#results would make the browser jump to that section (and keep re-jumping while the page loads),
// so the hash is taken out of the URL until loading has finished, then put back.
const START = location.hash;
if (START) history.replaceState(null, "", location.pathname + location.search);
window.addEventListener("load", () => {
  if (START && !location.hash) history.replaceState(null, "", location.pathname + location.search + START);
  window.scrollTo(0, 0);
});
const current = () => PAGES.find((p) => $("#" + p).classList.contains("on"));

// ------------------------------------------------------------------ selection
// Seasons with fewer than 2 crops reported in enough years have no LP (the server lists them in `blocked`).
// They stay in the menu, greyed out with the reason, so a missing season is explained rather than hidden.
const usable = (state) => (S.seasons[state] || []).filter((s) => !(S.blocked[state] || []).includes(s));
function fillSelects(state, season) {
  const st = $("#selState"), se = $("#selSeason"), off = S.blocked[state] || [];
  st.innerHTML = Object.keys(S.seasons).map((s) => { const none = !usable(s).length;
    return `<option value="${esc(s)}" ${s === state ? "selected" : ""} ${none ? "disabled" : ""}>${esc(s)}${none ? " (too few crops)" : ""}</option>`; }).join("");
  se.innerHTML = S.seasons[state].map((s) => { const no = off.includes(s);
    return `<option value="${esc(s)}" ${s === season ? "selected" : ""} ${no ? "disabled" : ""}>${esc(s)}${no ? " (too few crops)" : ""}</option>`; }).join("");
  st.disabled = se.disabled = false;
}
// A new state is kept: if the current season has no LP there, its first season that has one is used instead.
function selectState(state) {
  if (!S.seasons[state]) return;
  const ok = usable(state), se = $("#selSeason").value;
  if (!ok.length) return status(`${state}: no season has at least 2 crops reported in enough years for an LP.`, true);
  const season = ok.includes(se) ? se : ok[0];
  S.note = season === se ? null : S.seasons[state].includes(se) ? `${state} has too few ${se} crops for an LP, so ${season} is shown.`
    : `${state} has no ${se} season in the data, so ${season} is shown.`;
  fillSelects(state, season);
  run();
}
$("#selState").onchange = () => selectState($("#selState").value);
$("#selSeason").onchange = () => run();
// one model choice for the whole app: the Results toggle and the map toggles move together
function setModel(m) {
  S.model = m;
  document.body.dataset.model = m;                             // pages that follow the model fade to its colour
  $$("[data-model]").forEach((x) => { const on = +x.dataset.model === m; x.classList.toggle("on", on); x.setAttribute("aria-selected", on); });
  if (S.r) { renderModel(); draw(current()); }
}
$$("[data-model]").forEach((b) => b.onclick = () => setModel(+b.dataset.model));

async function run(retry = true) {
  const state = $("#selState").value, season = $("#selSeason").value, settings = { ...S.set };
  status(`Solving ${state} · ${season}…`);
  document.body.classList.add("loading");
  try {
    const bkey = `${state}|${season}`, custom = !isDefault(settings);
    const [r, ind, base] = await Promise.all([
      api("/api/run", { state, season, settings }),
      S.india[indiaKey(season)] ? Promise.resolve(S.india[indiaKey(season)]) : api("/api/india", { season, settings }),
      !custom || S.base[bkey] ? Promise.resolve(S.base[bkey]) : api("/api/run", { state, season }),
    ]);
    S.flash = !!S.last && S.last[0] === state && S.last[1] === season;   // only input changes flash, not a new state
    S.r = r; S.india[indiaKey(season)] = ind; S.last = [state, season, settings];
    S.base[bkey] = custom ? base : r;
    render();
    if (S.meta && r.data_version !== S.meta.data.version) setTimeout(checkData);
    status(S.note || `${r.coef.length} crops · ${r.years[0]}–${r.years[1]}`);
    S.note = null;
    draw(current());
    S.flash = false;
  } catch (e) {
    const moved = S.last && (S.last[0] !== state || S.last[1] !== season);
    if (retry && moved && !isDefault(settings)) {             // custom inputs have no solution here: stay, use defaults
      S.set = { ...DEF };
      S.note = `Your inputs have no solution for ${state} · ${season}, so the default inputs are shown.`;
      return run(false);
    }
    S.note = null;
    status(e.message, true);
    if (S.last) { fillSelects(S.last[0], S.last[1]); S.set = { ...S.last[2] }; }   // keep inputs consistent with what is shown
    if (S.r) renderInputs(e.message);
  } finally { document.body.classList.remove("loading"); }
}

// ------------------------------------------------------------------ model inputs
const BOUNDS = { historical: "Historical min to max", band: "Around average" };
const YIELD = { mean: "Mean", median: "Median", weighted: "Area-weighted" };
function renderInputs(err = "") {
  const st = S.set, lim = S.r.limits, o1 = S.r.opt1;
  $("#inLand").value = st.land_pct; $("#inTarget").value = st.target_pct; $("#inBand").value = st.band_pct; $("#inPulse").value = st.pulse_share;
  $("#vLand").textContent = `${st.land_pct}% · ${big(o1.L_hist * st.land_pct / 100)} ha`;
  $("#vTarget").textContent = `${st.target_pct}% · ${big(S.r.opt2.D_hist * st.target_pct / 100)} t`;
  $("#vBounds").textContent = st.bounds === "band" ? `±${st.band_pct}%` : "min–max";
  $("#vPulse").textContent = st.pulse_share ? `≥ ${st.pulse_share}%` : "off";
  $("#vYield").textContent = YIELD[st.yield_method];
  $("#bandRow").classList.toggle("hidden", st.bounds !== "band");
  $$("[data-bounds]").forEach((b) => b.classList.toggle("on", b.dataset.bounds === st.bounds));
  $$("[data-yield]").forEach((b) => b.classList.toggle("on", b.dataset.yield === st.yield_method));
  $("#hLand").textContent = `Needs at least ${fmt(lim.land_min_pct)}%: below that the crops' lower limits do not fit.`;
  $("#hTarget").textContent = `Reachable up to ${fmt(lim.target_max_pct)}%: every crop at its upper limit.`;
  $("#hBounds").textContent = st.bounds === "band" ? `Each crop stays within ±${st.band_pct}% of its average area.` : "Each crop between its smallest and largest yearly area.";
  $("#inPulse").disabled = !lim.has_pulses;
  $("#hPulse").textContent = lim.has_pulses ? `Historically ${fmt(lim.pulse_hist_pct, 1)}% · at most about ${fmt(lim.pulse_max_pct)}% possible.` : "No pulses in this state's LP.";
  $("#hYield").textContent = { mean: "Average of yearly yields (as in the report).", median: "Middle year; ignores unusual years.", weighted: "Total production ÷ total area." }[st.yield_method];
  const msg = $("#hLand").closest(".inputs");
  msg.querySelectorAll(".in-hint").forEach((h) => h.classList.remove("warn"));
  feasibility(lim);
  if (err) { const h = /Model 1/.test(err) && !/pulses/.test(err) ? "#hLand" : /Model 2/.test(err) && !/pulses/.test(err) ? "#hTarget" : "#hPulse";
    $(h).textContent = err; $(h).classList.add("warn"); }
  $("#activeList").innerHTML = [
    `Model 1 land ≤ ${st.land_pct}% of history`, `Model 2 output ≥ ${st.target_pct}% of history`,
    st.bounds === "band" ? `each crop within ±${st.band_pct}% of its average area` : "each crop within its historical min–max area",
    st.pulse_share && lim.has_pulses ? `pulses ≥ ${st.pulse_share}% of land` : "no pulse floor",
    `${YIELD[st.yield_method].toLowerCase()} yields`,
  ].map((x) => `<li>${x}</li>`).join("");
  $("#customBadge").classList.toggle("hidden", isDefault(st));
}
// Where each slider has a solution, from the limits of the last solve. The track shows that zone with a tick at
// history; dragging outside it turns the card to the warning colour before the LP is even run.
const FEAS = {
  inLand: { zone: (l) => [l.land_min_pct, Infinity], mark: () => 100,
    why: (v, l) => `${v}% is below the ${fmt(l.land_min_pct)}% the crops' lower limits need: Model 1 has no solution.` },
  inTarget: { zone: (l) => [-Infinity, l.target_max_pct], mark: () => 100,
    why: (v, l) => `${v}% is above the ${fmt(l.target_max_pct)}% reachable with every crop at its upper limit: Model 2 has no solution.` },
  inPulse: { zone: (l) => [-Infinity, l.pulse_max_pct], mark: (l) => l.pulse_hist_pct,
    why: (v, l) => `${v}% is above the about ${fmt(l.pulse_max_pct)}% possible within the area limits: no solution.` },
};
function feasibility(lim) {
  for (const [id, f] of Object.entries(FEAS)) {
    const el = $("#" + id), card = el.closest(".input");
    if (el.disabled) { el.style.removeProperty("--track"); card.classList.remove("bad"); continue; }
    const lo = +el.min, hi = +el.max, v = +el.value, [a, b] = f.zone(lim), m = f.mark(lim);
    const at = (x, d = 0) => `calc(8px + (100% - 16px) * ${Math.max(0, Math.min(1, (x - lo) / (hi - lo)))} + ${d}px)`;   // thumb centre
    el.style.setProperty("--track",
      `linear-gradient(to right, transparent ${at(m, -1)}, var(--ink) ${at(m, -1)} ${at(m, 1)}, transparent ${at(m, 1)}),` +
      `linear-gradient(to right, var(--warn-mid) ${at(a)}, var(--acc-mid) ${at(a)} ${at(b)}, var(--warn-mid) ${at(b)})`);
    const bad = v !== 0 && (v < a || v > b);
    card.classList.toggle("bad", bad);
    if (bad) { const h = card.querySelector(".in-hint"); h.textContent = f.why(v, lim); h.classList.add("warn"); }
  }
}
function setInput(k, v) { S.set[k] = v; renderInputs(); run(); }
for (const [id, k] of [["#inLand", "land_pct"], ["#inTarget", "target_pct"], ["#inBand", "band_pct"], ["#inPulse", "pulse_share"]]) {
  $(id).oninput = () => { S.set[k] = +$(id).value; renderInputs(); };
  $(id).onchange = () => setInput(k, +$(id).value);
}
$$("[data-bounds]").forEach((b) => b.onclick = () => setInput("bounds", b.dataset.bounds));
$$("[data-yield]").forEach((b) => b.onclick = () => setInput("yield_method", b.dataset.yield));
$("#btnReset").onclick = () => { S.set = { ...DEF }; renderInputs(); run(); };

function renderEffect() {
  const r = S.r, b = S.base[`${r.state}|${r.season}`] || r, custom = !isDefault(S.set);
  const pulseShare = (res) => { const a = res.opt1.alloc, tot = a.reduce((t, d) => t + d.x_opt, 0);
    return 100 * a.filter((d) => res.pulse_crops.includes(d.Crop)).reduce((t, d) => t + d.x_opt, 0) / tot; };
  const was = (v) => (custom ? `default ${v}` : "default inputs");
  kpis("#kpiEffect", [
    ["Model 1 · output vs history", N(r.opt1.gain_pct, (x) => pct(x)), was(pct(b.opt1.gain_pct)), r.opt1.gain_pct > 0, 1],
    ["Model 2 · land vs history", N(-r.opt2.saving_pct, (x) => pct(x)), was(pct(-b.opt2.saving_pct)), r.opt2.saving_pct > 0, 2],
    ["Value of one more hectare", N(r.opt1.lam, (x) => fmt(x, 2) + " t"), was(fmt(b.opt1.lam, 2) + " t")],
    ["Pulses in Model 1 plan", r.limits.has_pulses ? N(pulseShare(r), (x) => fmt(x, 1) + "%") : "–", r.limits.has_pulses ? was(fmt(pulseShare(b), 1) + "%") : "no pulses"],
  ]);
  $("#effectNote").textContent = custom ? "Bars compare the Model 1 plan under your inputs with the plan under the default inputs."
    : "Change an input above to compare. With the defaults, the bars compare history with the Model 1 plan.";
}

// ------------------------------------------------------------------ text and tables
function render() {
  const r = S.r, o1 = r.opt1, o2 = r.opt2, p = r.profile;
  $$("[data-scope]").forEach((el) => el.textContent = `${r.state} · ${r.season} · ${r.years[0]}–${r.years[1]}`);
  $("#mapSeason").textContent = `${r.season} season`;

  const gap = o1.scipy_Z != null ? Math.abs(o1.Z - o1.scipy_Z) / o1.Z : null;
  $("#agree").innerHTML = gap != null ? `This run: both solvers agree to ${gap < 1e-9 ? "&lt; 10⁻⁹" : gap.toExponential(1)} (relative).` : "";

  kpis("#kpiOverview", [
    ["Output on the same land", N(o1.gain_pct, (x) => pct(x)), "Model 1", true, 1],
    ["Land for the same output", N(-o2.saving_pct, (x) => pct(x)), "Model 2", true, 2],
    ["Crops in the LP", N(r.coef.length, (x) => fmt(x)), `${r.excluded.length} excluded for units`],
    ["Value of one more hectare", N(o1.lam, (x) => fmt(x, 2) + " t"), "shadow price λ*"],
  ]);
  kpis("#kpiState", [
    ["Records", N(p.records, (x) => fmt(x)), `${r.years[0]}–${r.years[1]}`],
    ["Districts modelled", N(p.districts, (x) => fmt(x)), "solved separately"],
    ["Crops grown", N(p.crops, (x) => fmt(x)), `${r.coef.length} enter the LP`],
    ["LP crop area per year", N(p.area, big), `ha · ${big(p.production)} t output`],
  ]);

  const c = r.cleaning, dup = c.steps.find((s) => s.step.startsWith("Stacked"));
  $("#cleaning").innerHTML = `<p><b>${fmt(c.rows_in)}</b> rows → <b>${fmt(c.rows_out)}</b> after cleaning</p>` +
    table([{ k: "step", label: "Removed (whole dataset)" }, { k: "removed", label: "Rows", r: 1, f: (v) => "−" + fmt(v) }], c.steps.filter((s) => s.removed > 0));
  $("#dataFile").textContent = `${r.data.file} · saved ${when(r.data.modified)}`;
  $("#dataRows").textContent = `${fmt(c.rows_in)} lines read, ${fmt(c.rows_out)} records used`;
  $("#dataDup").textContent = dup ? dup.note : "–";
  const typo = r.unusual.filter((u) => u.yield_ / u.median > 100);   // droughts push yields down, unit slips push them up
  $("#unusual").classList.toggle("hidden", !r.unusual.length);
  $("#unusual").innerHTML = r.unusual.length ? `<details class="lines${typo.length ? " alert" : ""}"${typo.length ? " open" : ""}><summary>${fmt(r.unusual_total)} row${r.unusual_total > 1 ? "s" : ""}
    far from the crop's usual yield here${typo.length ? ` · <span class="flag">${typo.length} more than 100× above: likely a typo or unit slip</span>` : ""}</summary>
    <p class="note">Yield more than 10× above or below the crop's median in ${esc(r.state)} · ${esc(r.season)}: droughts, very small plots, or typos.
    They are kept, so a typo moves the crop's yield y<sub>c</sub>; fix or delete such lines in the CSV. The ${r.unusual.length} furthest:</p>` +
    table([{ k: "line", label: "CSV line", r: 1, f: (v) => fmt(v) }, { k: "crop", label: "Crop" }, { k: "district", label: "District", f: (v) => esc(title(v)) },
      { k: "year", label: "Year" }, { k: "area", label: "Area (ha)", r: 1, f: (v) => fmt(v) }, { k: "prod", label: "Production (t)", r: 1, f: (v) => fmt(v, 1) },
      { k: "yield_", label: "Yield", r: 1, f: (v, u) => `<span class="${typo.includes(u) ? "flag" : ""}">${fmt(v, 3)}</span>` },
      { k: "median", label: "Usual", r: 1, f: (v) => fmt(v, 3) }], r.unusual) + "</details>" : "";
  const tc = $("#selTrace"), keep = tc.value, crops = [...r.coef].sort((a, b) => b.hist_area - a.hist_area).map((d) => d.Crop);
  tc.innerHTML = crops.map((x) => `<option ${x === keep ? "selected" : ""}>${esc(x)}</option>`).join("");
  $("#excluded").innerHTML = r.excluded.length
    ? "<div style='height:14px'></div>" + table([{ k: "Crop", label: `Excluded here (${r.state})` }, { k: "reason", label: "Reason" }], r.excluded) : "";

  renderModel();
  interpret();
  renderChips();
  renderInputs();
  renderEffect();
}

const DECISION = (s) => (s.startsWith("at max") ? "expand" : s.startsWith("at min") ? "cut" : "marginal");
function renderChips() {
  const r = S.r, crops = [...r.opt1.alloc].sort((a, b) => b.hist_area - a.hist_area);
  if (!crops.some((c) => c.Crop === S.crop)) S.crop = crops[0].Crop;
  $("#cropChips").innerHTML = crops.map((c) =>
    `<button type="button" class="chip${c.Crop === S.crop ? " on" : ""}" data-crop="${esc(c.Crop)}">${esc(c.Crop)}<small>${DECISION(c.bound_status)}</small></button>`).join("");
  $$("[data-crop]").forEach((b) => b.onclick = () => { S.crop = b.dataset.crop; renderChips(); draw("crops"); });
}

function renderModel() {
  const r = S.r, o1 = r.opt1, o2 = r.opt2, uh = " (t)";
  if (S.model === 1) {
    kpis("#kpiModel", [["Land available (ha)", N(o1.L, (x) => fmt(x)), `${S.set.land_pct}% of history`], [`Historical output${uh}`, N(o1.D_hist, (x) => fmt(x))],
      [`Optimal output${uh}`, N(o1.Z, (x) => fmt(x))], ["Change vs history", N(o1.gain_pct, (x) => pct(x)), "", o1.gain_pct > 0]], "m1");
    $("#modelNote").textContent = `Shadow price of land λ* = ${fmt(o1.lam, 4)} t: one more hectare adds this much output.`;
  } else {
    kpis("#kpiModel", [[`Output target${uh}`, N(o2.D, (x) => fmt(x)), `${S.set.target_pct}% of history`], ["Historical land (ha)", N(o2.L_hist, (x) => fmt(x))],
      ["Minimum land (ha)", N(o2.land, (x) => fmt(x))], ["Change vs history", N(-o2.saving_pct, (x) => pct(x)), "", o2.saving_pct > 0]], "m2");
    $("#modelNote").textContent = o2.inv_lam != null
      ? `Duality check: μ* = ${fmt(o2.mu, 4)} ha per tonne, and 1/λ* at that land = ${fmt(o2.inv_lam, 4)}.` +
        (Math.abs(o2.mu - o2.inv_lam) < 1e-6 * o2.mu ? " They match." : "") : "";
  }
  // check the solution against the constraints, from the allocation table alone
  const a = (S.model === 1 ? o1 : o2).alloc, sx = a.reduce((s, d) => s + d.x_opt, 0), sy = a.reduce((s, d) => s + d.y_c * d.x_opt, 0);
  const near = (u, v) => Math.abs(u - v) <= 1e-6 * Math.max(1, Math.abs(v)) + 0.01;
  const inb = a.every((d) => d.x_opt >= d.a_c - 0.01 && d.x_opt <= d.m_c + 0.01);
  const mark = (ok) => `<span class="${ok ? "ok" : "no"}">${ok ? "✓" : "✗"}</span>`;
  $("#modelCheck").innerHTML = "Check from the table below: " + (S.model === 1
    ? `Σ x<sub>c</sub> = ${fmt(sx)} ha ${sx <= o1.L + 0.01 ? "≤" : ">"} L ${mark(sx <= o1.L + 0.01)} · Σ y<sub>c</sub>x<sub>c</sub> = ${fmt(sy)} t = Z* ${mark(near(sy, o1.Z))}`
    : `Σ y<sub>c</sub>x<sub>c</sub> = ${fmt(sy)} t ${sy >= o2.D - 0.01 ? "≥" : "<"} target ${mark(sy >= o2.D - 0.01)} · Σ x<sub>c</sub> = ${fmt(sx)} ha = minimum land ${mark(near(sx, o2.land))}`) +
    ` · every crop within [a<sub>c</sub>, m<sub>c</sub>] ${mark(inb)}` +
    (r.pulse_active ? (() => { const ps = a.filter((d) => r.pulse_crops.includes(d.Crop)).reduce((s, d) => s + d.x_opt, 0) / sx;
      return ` · pulses ${fmt(100 * ps, 1)}% ≥ ${S.set.pulse_share}% ${mark(ps >= S.set.pulse_share / 100 - 1e-6)}`; })() : "");
  const x2 = Object.fromEntries(o2.alloc.map((d) => [d.Crop, d.x_opt]));
  const st = (s) => (s.startsWith("at max") ? "at max" : s.startsWith("at min") ? "at min" : "between bounds");
  const s2 = Object.fromEntries(o2.alloc.map((d) => [d.Crop, st(d.bound_status)]));
  $("#allocTable").innerHTML = table([
    { k: "Crop", label: "Crop" },
    { k: "y_c", label: "Yield y<sub>c</sub> (t/ha)", r: 1, f: (v) => fmt(v, 2) },
    { k: "a_c", label: "Min a<sub>c</sub>", r: 1, f: (v) => fmt(v) },
    { k: "m_c", label: "Max m<sub>c</sub>", r: 1, f: (v) => fmt(v) },
    { k: "hist_area", label: "Historical", r: 1, f: (v) => fmt(v) },
    { k: "x_opt", label: "Model 1", r: 1, cls: S.model === 1 ? "act" : "", f: (v) => (S.model === 1 ? `<b>${fmt(v)}</b>` : fmt(v)) },
    { k: "Crop", label: "Model 2", r: 1, cls: S.model === 2 ? "act" : "", f: (v) => (S.model === 2 ? `<b>${fmt(x2[v])}</b>` : fmt(x2[v])) },
    { k: "bound_status", label: "Decision", f: (v, row) => (S.model === 1 ? st(v) : s2[row.Crop]) },
  ], o1.alloc);
}

function interpret() {
  const r = S.r, al = r.opt1.alloc, o1 = r.opt1, o2 = r.opt2;
  const up = al.filter((d) => d.bound_status.startsWith("at max")).map((d) => d.Crop);
  const dn = al.filter((d) => d.bound_status.startsWith("at min")).map((d) => d.Crop);
  const basic = al.find((d) => d.bound_status.startsWith("basic"));
  const b10 = r.band.find((b) => b.band_pct === 10);
  const items = [
    `<b>Q1:</b> on ${fmt(o1.L)} ha (${S.set.land_pct}% of historical land), output goes from ${fmt(o1.D_hist)} to ${fmt(o1.Z)} t (<b>${pct(o1.gain_pct)}</b>).`,
    `<b>Q2:</b> ${S.set.target_pct === 100 ? "the historical output" : `${S.set.target_pct}% of historical output`} can be produced on ${fmt(o2.land)} ha, <b>${pct(-o2.saving_pct)} land</b> vs history.`,
    isDefault(S.set) ? "" : `These results use custom inputs (see Model inputs).`,
    up.length ? `Land moves to the high-yield crops (${list(up)}), which reach their historical maximum.` : "",
    dn.length ? `${dn.length} lower-yield crop${dn.length > 1 ? "s are" : " is"} held at the historical minimum.` : "",
    basic ? `${basic.Crop} takes the remaining land; one more hectare is worth ${fmt(o1.lam, 2)} t (λ*).` : "",
    b10 ? `With a cautious ±10% limit per crop, the gain is ${pct(b10.output_gain_pct)} output or ${fmt(b10.land_saving_pct, 1)}% less land.` : "",
  ];
  if (r.districts.length > 1) {
    const d = [...r.districts].sort((p, q) => q.output_gain_pct - p.output_gain_pct);
    items.push(`Across ${d.length} districts the gain ranges from ${pct(d[d.length - 1].output_gain_pct)} (${title(d[d.length - 1].District)}) ` +
      `to ${pct(d[0].output_gain_pct)} (${title(d[0].District)}).`);
  }
  const ind = S.india[indiaKey(r.season)];
  if (ind && ind.length > 1) {
    const rank = [...ind].sort((a, b) => b.gain_pct - a.gain_pct).findIndex((x) => x.state === r.state) + 1;
    if (rank) items.push(`Among ${ind.length} states solved for ${r.season}, ${r.state} ranks ${rank} by output gain.`);
  }
  $("#interp").innerHTML = items.filter(Boolean).map((s) => `<li>${s}</li>`).join("");
}

// ------------------------------------------------------------------ checking the numbers by hand
const median = (v) => { const s = [...v].sort((a, b) => a - b), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
$("#selTrace").onchange = () => renderTrace();
async function renderTrace() {
  const r = S.r, crop = $("#selTrace").value;
  if (!r || !crop) return;
  const key = [r.state, r.season, crop, S.set.yield_method, r.data_version].join("|");
  const q = new URLSearchParams({ state: r.state, season: r.season, crop, yield_method: S.set.yield_method });
  const t = S.trace[key] || (S.trace[key] = await api(`/api/trace?${q}`));
  if ($("#selTrace").value !== crop || S.r !== r) return;
  const W = t.by_year.filter((y) => y.in_window), n = W.length;
  const lo = W.reduce((a, b) => (b.area < a.area ? b : a)), hi = W.reduce((a, b) => (b.area > a.area ? b : a));
  const sumY = W.reduce((s, y) => s + y.yield_, 0), sumA = W.reduce((s, y) => s + y.area, 0), sumP = W.reduce((s, y) => s + y.prod, 0);
  const yc = { mean: sumY / n, median: median(W.map((y) => y.yield_)), weighted: sumP / sumA }[t.yield_method];
  const F = {
    mean: `y<sub>c</sub> = (1/n) Σ<sub>t</sub> P<sub>t</sub>/A<sub>t</sub> = <b>${fmt(sumY, 4)} / ${n} = ${fmt(yc, 4)}</b> t/ha<small>mean of the ${n} yearly yields in the table</small>`,
    median: `y<sub>c</sub> = median<sub>t</sub> P<sub>t</sub>/A<sub>t</sub> = <b>${fmt(yc, 4)}</b> t/ha<small>middle of the ${n} yearly yields in the table</small>`,
    weighted: `y<sub>c</sub> = Σ P<sub>t</sub> / Σ A<sub>t</sub> = <b>${fmt(sumP)} / ${fmt(sumA)} = ${fmt(yc, 4)}</b> t/ha<small>all production over all area, ${n} years</small>`,
  }[t.yield_method];
  const c = t.coef, same = (u, v) => Math.abs(u - v) <= 1e-4 * Math.max(1, Math.abs(v));
  const ok = c && same(yc, c.y_c) && same(lo.area, c.a_c) && same(hi.area, c.m_c) && same(sumA / n, c.hist_area);
  $("#traceMath").innerHTML = `
    <p class="f">${F}</p>
    <p class="f">a<sub>c</sub> = min<sub>t</sub> A<sub>t</sub> = <b>${fmt(lo.area)} ha</b><small>lower area limit: ${lo.Crop_Year}, the brown row</small></p>
    <p class="f">m<sub>c</sub> = max<sub>t</sub> A<sub>t</sub> = <b>${fmt(hi.area)} ha</b><small>upper area limit: ${hi.Crop_Year}, the green row</small></p>
    <p class="f">h<sub>c</sub> = (1/n) Σ<sub>t</sub> A<sub>t</sub> = <b>${fmt(sumA / n)} ha</b><small>historical area per year: the baseline the plan is compared with</small></p>
    <p class="checks">${c ? `The LP uses y<sub>c</sub> = ${fmt(c.y_c, 4)}, a<sub>c</sub> = ${fmt(c.a_c)}, m<sub>c</sub> = ${fmt(c.m_c)}, h<sub>c</sub> = ${fmt(c.hist_area)}:
      <span class="${ok ? "ok" : "no"}">${ok ? "✓ same as worked out here" : "✗ differs"}</span>` : `<span class="no">Not in the LP</span>: ${esc(t.why)}.`}
      Years ${t.years[0]}–${t.years[1]}; a crop needs at least ${t.min_years} of them.</p>`;
  $("#traceYears").innerHTML = `<table><thead><tr><th>Year</th><th class="r">Lines</th><th class="r">Area A<sub>t</sub> (ha)</th><th class="r">Production P<sub>t</sub> (t)</th><th class="r">P<sub>t</sub>/A<sub>t</sub></th></tr></thead><tbody>${
    t.by_year.map((y) => `<tr class="${!y.in_window ? "out" : y === lo ? "lo" : y === hi ? "hi" : ""}"><td>${y.Crop_Year}${y.in_window ? "" : " <small>not averaged</small>"}</td>
      <td class="r">${y.n}</td><td class="r">${fmt(y.area)}</td><td class="r">${fmt(y.prod, 1)}</td><td class="r">${fmt(y.yield_, 4)}</td></tr>`).join("")}</tbody></table>`;
  const odd = new Set(r.unusual.map((u) => u.line));
  $("#traceLines summary").textContent = `The ${fmt(t.lines.length)} CSV lines behind this table`;
  $("#traceLinesNote").innerHTML = t.boundary_line
    ? `Each year's area and production are the sums of these lines (districts). The file holds a second release of the data from line
       ${fmt(t.boundary_line)} on, with production ×${t.factor}; it is divided back. A 1997–2015 record is on two lines and the first is used,
       so <b>to remove a record, delete both lines</b>; editing the unused line changes nothing.`
    : `Each year's area and production are the sums of these lines. ${t.split ? `The rows of the file were re-ordered, so each row's unit was decided from its year and yield (approximate); keep the original row order for exact results.` : ""}`;
  $("#traceLines .table-wrap").innerHTML = table([
    { k: "line", label: "CSV line", r: 1, f: (v) => fmt(v) }, { k: "year", label: "Year" }, { k: "district", label: "District", f: (v) => esc(title(v)) },
    { k: "area", label: "Area (ha)", r: 1, f: (v) => fmt(v) }, { k: "prod", label: "Production (t)", r: 1, f: (v) => fmt(v, 1) },
    { k: "line", label: "Note", f: (v, row) => [row.divided ? `÷${t.factor} (second release)` : "", row.twin ? `also on line ${fmt(row.twin)}, not used` : "",
      odd.has(v) ? `<span class="flag">yield ${fmt(row.prod / row.area, 3)} t/ha, far from usual</span>` : ""].filter(Boolean).join(" · ") },
  ], t.lines);
}

// ------------------------------------------------------------------ the data file can be edited while the app runs
const when = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "medium" });
async function checkData() {
  if (S.checking || document.hidden || !S.meta || !S.r) return;
  S.checking = true;
  let dimmed = false;
  try {
    const v = await api("/api/version");
    if (v.version === S.meta.data.version) return;
    status("Data file changed: reloading and re-solving…");
    document.body.classList.add("loading"); dimmed = true;
    const m = await api("/api/meta");                             // reads and cleans the edited file
    if (m.data.version !== S.meta.data.version) {
      S.meta = m; S.seasons = m.seasons; S.blocked = m.blocked || {};
      S.india = {}; S.base = {}; S.cropData = {}; S.trace = {};
      const st = usable($("#selState").value).length ? $("#selState").value : m.state, ok = usable(st);
      fillSelects(st, ok.includes($("#selSeason").value) ? $("#selSeason").value : ok[0]);
      S.note = `Data file changed (saved ${when(m.data.modified)}): re-solved with the edited data.`;
      await run();
    } else if (m.data.error) { S.meta.data.version = v.version; status(m.data.error, true); }
  } catch (e) { /* server busy or restarting: try again next time */ } finally { S.checking = false; if (dimmed) document.body.classList.remove("loading"); }
}
setInterval(checkData, 2000);

// ------------------------------------------------------------------ charts (drawn when their page is visible)
// what the India and district maps show for each model
const METRIC = {
  1: { st: "gain_pct", di: "output_gain_pct", label: "gain", title: "Output gain", note: "Model 1: extra output on the same land.",
    hover: (v) => pct(v), scale: SCALE, hi: ACC, lo: ACC_L },
  2: { st: "saving_pct", di: "land_saving_pct", label: "saved", title: "Land saved", note: "Model 2: land freed while keeping the historical output.",
    hover: (v) => fmt(v, 1) + "%", scale: SCALE2, hi: SOIL, lo: SOIL_L },
};
const CHARTS = {
  async overview(r) {
    if (!S.geo) S.geo = await (await fetch("/static/india_states.json")).json();
    const ind = S.india[indiaKey(r.season)] || [], M = METRIC[S.model], v = (x) => x[M.st];
    $("#mapTitle").textContent = `${M.title} by state`;
    $("#mapNote").textContent = `${M.note}${ind.some((x) => v(x) < 0) ? " Grey: worse than history." : ""} Click a state to load it.`;
    $("#rankNote").textContent = `${M.title} (Model ${S.model}), all states.`;
    map("#chIndia", S.geo, ind.map((x) => x.state), ind.map(v),
      ind.map((x) => `<b>${x.state}</b><br>output gain ${pct(x.gain_pct)}<br>land saved ${fmt(x.saving_pct, 1)}%<br>${x.crops} crops`),
      { pick: r.state, onClick: selectState, height: 520, label: M.label, scale: M.scale });
    const s = [...ind].sort((a, b) => v(a) - v(b));
    plot("#chStates", [{ type: "bar", orientation: "h", y: s.map((x) => x.state), x: s.map(v),
      marker: { color: s.map((x) => (x.state === r.state ? M.hi : M.lo)) }, hovertemplate: `%{y}: %{x:${S.model === 1 ? "+" : ""}.1f}%<extra></extra>` }],
      { showlegend: false, margin: { l: 150, r: 16, t: 8, b: 40 }, xaxis: { ticksuffix: "%" }, yaxis: { tickfont: { size: 11 } } }, 520);
    const el = $("#chStates"); el.removeAllListeners?.("plotly_click"); el.on("plotly_click", (e) => selectState(e.points[0].y));
  },
  data(r) {
    renderTrace();
    const ca = [...r.crop_area].reverse();
    plot("#chCropArea", [{ type: "bar", orientation: "h", y: ca.map((d) => d.Crop), x: ca.map((d) => d.area),
      marker: { color: ca.map((d) => (d.pooled ? ACC : GREY)) }, hovertemplate: "%{y}: %{x:,.0f} ha/yr<extra></extra>" }],
      { showlegend: false, xaxis: { title: "hectares per year" } }, 380);
    plot("#chYearly", [
      { type: "scatter", mode: "lines+markers", name: "Area (ha)", x: r.yearly.x, y: r.yearly.area, line: { color: MUTED, width: 2 }, marker: { size: 5 } },
      { type: "scatter", mode: "lines+markers", name: "Production (t)", x: r.yearly.x, y: r.yearly.prod, yaxis: "y2", line: { color: ACC, width: 2.5 }, marker: { size: 5 } },
    ], { yaxis: { title: "area (ha)" }, yaxis2: { title: { text: "production (t)", font: { size: 12, color: MUTED } }, overlaying: "y", side: "right", fixedrange: true, showgrid: false },
      margin: { l: 60, r: 60, t: 8, b: 40 } }, 380);
    plot("#chTrend", Object.entries(r.trend).map(([c, t], i) => ({ type: "scatter", mode: "lines", name: c, x: t.x, y: t.y,
      line: { color: TREND[i % TREND.length], width: 2, dash: i === 4 ? "dot" : "solid" }, hovertemplate: `${c} %{x}: %{y:.2f} t/ha<extra></extra>` })),
      { yaxis: { title: "yield (t/ha)" } }, 320);
    const yrs = Object.keys(r.rows_per_year).map(Number), inWin = (y) => y >= r.years[0] && y <= r.years[1];
    plot("#chYears", [{ type: "bar", x: yrs, y: yrs.map((y) => r.rows_per_year[y]), marker: { color: yrs.map((y) => (inWin(y) ? ACC : GREY)) },
      hovertemplate: "%{x}: %{y:,} records<extra></extra>" }], { showlegend: false, yaxis: { title: "records" } }, 320);
    const c = [...r.coef].sort((a, b) => b.y_c - a.y_c);
    plot("#chYield", [{ type: "bar", x: c.map((d) => d.Crop), y: c.map((d) => d.y_c), marker: { color: ACC },
      error_y: { type: "data", array: c.map((d) => d.yield_sd), color: INK, thickness: 1.1, width: 3 },
      hovertemplate: "%{x}: %{y:.2f} t/ha<extra></extra>" }],
      { showlegend: false, yaxis: { title: "yield (t/ha)" }, xaxis: { tickangle: -40 } }, 380);
  },
  results(r) {
    const o = S.model === 1 ? r.opt1 : r.opt2, label = `Model ${S.model}`, MC = MODEL_COL(S.model);
    const a = [...o.alloc].sort((p, q) => p.y_c - q.y_c), h = Math.max(320, 22 * a.length + 80);
    plot("#chAlloc", [
      { type: "bar", orientation: "h", name: "Historical", y: a.map((d) => d.Crop), x: a.map((d) => d.hist_area), marker: { color: GREY },
        hovertemplate: "%{y}: %{x:,.0f} ha<extra>historical</extra>" },
      { type: "bar", orientation: "h", name: label, y: a.map((d) => d.Crop), x: a.map((d) => d.x_opt), marker: { color: MC },
        hovertemplate: `%{y}: %{x:,.0f} ha<extra>${label}</extra>` },
    ], { barmode: "group", xaxis: { title: "hectares" } }, h);
    plot("#chChange", [{ type: "bar", orientation: "h", y: a.map((d) => d.Crop), x: a.map((d) => d.change_ha),
      marker: { color: a.map((d) => (d.change_ha >= 0 ? MC : GREY)) }, hovertemplate: "%{y}: %{x:+,.0f} ha<extra></extra>" }],
      { showlegend: false, xaxis: { title: `hectares gained (${S.model === 1 ? "green" : "brown"}) or given up (grey)`, zeroline: true, zerolinecolor: INK } }, h);
    const w = [...o.alloc].sort((p, q) => q.y_c - p.y_c).filter((d) => Math.abs(d.y_c * d.change_ha) > 1e-6);
    plot("#chOutput", [{ type: "waterfall", orientation: "v", x: [...w.map((d) => d.Crop), "Total"],
      y: [...w.map((d) => d.y_c * d.change_ha), 0], measure: [...w.map(() => "relative"), "total"],
      increasing: { marker: { color: MC } }, decreasing: { marker: { color: GREY } }, totals: { marker: { color: INK } },
      connector: { line: { color: "#ddd", width: 1 } }, hovertemplate: "%{x}: %{y:+,.0f} t<extra></extra>" }],
      { showlegend: false, yaxis: { title: "output change (t)" }, xaxis: { tickangle: -40 }, transition: { duration: 0 } }, 380);
  },
  model(r) {
    const b = S.base[`${r.state}|${r.season}`] || r, custom = !isDefault(S.set);
    const now = Object.fromEntries(r.opt1.alloc.map((d) => [d.Crop, d.x_opt]));
    const a = [...b.opt1.alloc].sort((p, q) => p.y_c - q.y_c);
    const first = custom ? { name: "Default inputs", x: a.map((d) => d.x_opt) } : { name: "Historical", x: a.map((d) => d.hist_area) };
    plot("#chCompare", [
      { type: "bar", orientation: "h", name: first.name, y: a.map((d) => d.Crop), x: first.x, marker: { color: GREY },
        hovertemplate: `%{y}: %{x:,.0f} ha<extra>${first.name}</extra>` },
      { type: "bar", orientation: "h", name: custom ? "Your inputs" : "Model 1 plan", y: a.map((d) => d.Crop), x: a.map((d) => now[d.Crop] ?? 0),
        marker: { color: ACC }, hovertemplate: "%{y}: %{x:,.0f} ha<extra>plan</extra>" },
    ], { barmode: "group", xaxis: { title: "hectares (Model 1)" } }, Math.max(320, 22 * a.length + 80));
  },
  async crops(r) {
    if (!S.geo) S.geo = await (await fetch("/static/india_states.json")).json();
    const crop = S.crop, key = `${crop}|${r.season}`;
    if (!S.cropData[key]) S.cropData[key] = await api(`/api/crop?crop=${encodeURIComponent(crop)}&season=${encodeURIComponent(r.season)}`);
    if (crop !== S.crop) return;                                  // another chip was clicked meanwhile
    const rows = S.cropData[key], a = r.opt1.alloc.find((x) => x.Crop === crop);
    const sorted = [...rows].sort((p, q) => q.yield_ - p.yield_), rank = sorted.findIndex((x) => x.state === r.state) + 1;
    const here = rows.find((x) => x.state === r.state);
    kpis("#kpiCrop", [
      ["Yield here", N(here ? here.yield_ : null, (x) => fmt(x, 2) + " t/ha"), `LP coefficient y<sub>c</sub> = ${fmt(a.y_c, 2)}`],
      ["Rank in India", rank ? `${rank} of ${rows.length}` : "–", `states growing ${crop} in ${r.season}`],
      ["Model 1 decision", DECISION(a.bound_status), a.bound_status.startsWith("basic") ? "takes the remaining land" : "bound reached"],
      ["Change in area", N(a.change_ha, (x) => (x >= 0 ? "+" : "−") + fmt(Math.abs(x)) + " ha"), `${pct(100 * a.change_ha / a.hist_area)} vs history`, a.change_ha > 0],
    ], crop);
    $("#cropMapNote").textContent = `${crop} · ${r.season}`;
    map("#chCropMap", S.geo, rows.map((x) => x.state), rows.map((x) => x.yield_),
      rows.map((x) => `<b>${x.state}</b><br>${crop}: ${fmt(x.yield_, 2)} t/ha<br>${big(x.area)} ha per year`),
      { pick: r.state, onClick: selectState, height: 520, suffix: "", label: "t/ha" });
    const top = sorted.slice(0, 20);
    if (here && !top.includes(here)) top.push(here);
    const b = top.reverse();
    plot("#chCropRank", [{ type: "bar", orientation: "h", y: b.map((x) => x.state), x: b.map((x) => x.yield_),
      marker: { color: b.map((x) => (x.state === r.state ? ACC : ACC_L)) }, hovertemplate: "%{y}: %{x:.2f} t/ha<extra></extra>" }],
      { showlegend: false, margin: { l: 150, r: 16, t: 8, b: 40 }, xaxis: { title: "yield (t/ha)" }, yaxis: { tickfont: { size: 11 } } }, 520);
    const el = $("#chCropRank"); el.removeAllListeners?.("plotly_click"); el.on("plotly_click", (e) => selectState(e.points[0].y));
  },
  sensitivity(r) {
    const L0 = r.opt1.L;
    const vline = (ys) => ({ type: "scatter", mode: "lines", name: "Historical land", x: [L0, L0], y: ys, line: { color: MUTED, dash: "dot", width: 1.5 }, hoverinfo: "skip" });
    plot("#chCurve", [{ type: "scatter", mode: "lines", name: "Z*(L)", x: r.curve.L, y: r.curve.Z, line: { color: ACC, width: 2.5 },
      fill: "tozeroy", fillcolor: "rgba(47,111,78,.08)", hovertemplate: "L = %{x:,.0f} ha<br>Z* = %{y:,.0f} t<extra></extra>" },
      vline([0, Math.max(...r.curve.Z)])], { xaxis: { title: "land budget L (ha)" }, yaxis: { title: "optimal output (t)" } }, 300);
    const lam = r.curve.lam.map((v) => v ?? null);
    plot("#chLam", [{ type: "scatter", mode: "lines", name: "λ*(L)", x: r.curve.L, y: lam, line: { color: ACC, width: 2.5, shape: "hv" },
      hovertemplate: "L = %{x:,.0f} ha<br>λ* = %{y:.3f} t/ha<extra></extra>" }, vline([0, Math.max(...lam.filter((v) => v != null))])],
      { xaxis: { title: "land budget L (ha)" }, yaxis: { title: "λ* (t per ha)" } }, 300);
    plot("#chBand", [
      { type: "scatter", mode: "lines+markers", name: "Model 1: output gain %", x: r.band.map((b) => b.band_pct), y: r.band.map((b) => b.output_gain_pct),
        line: { color: ACC, width: 2.5 }, marker: { size: 7 }, hovertemplate: "±%{x}%: %{y:+.1f}%<extra></extra>" },
      { type: "scatter", mode: "lines+markers", name: "Model 2: land saved %", x: r.band.map((b) => b.band_pct), y: r.band.map((b) => b.land_saving_pct),
        line: { color: SOIL, width: 2.5, dash: "dash" }, marker: { size: 7 }, hovertemplate: "±%{x}%: %{y:.1f}%<extra></extra>" },
    ], { xaxis: { title: "each crop may change by ±p% of its average area", ticksuffix: "%" }, yaxis: { title: "%" } }, 300);
  },
  districts(r) {
    const has = r.districts.length > 1;
    $("#distNote").textContent = has ? `Both models solved separately for each of ${r.districts.length} districts in ${r.state}, each with its own land, output and bounds.`
      : `${r.state} has fewer than two districts with enough ${r.season} data to compare.`;
    $$("#districts .charts").forEach((el) => el.classList.toggle("hidden", !has));
    if (!has) return;
    const M = METRIC[S.model], d = [...r.districts].sort((p, q) => p[M.di] - q[M.di]);
    $("#distMapTitle").textContent = `${M.title} on the map`;
    if (r.district_geo && r.district_geo.features.length) {
      const g = Object.fromEntries(d.map((x) => [x.District, x]));
      const ids = r.district_geo.features.map((f) => f.id);
      map("#chDistMap", r.district_geo, ids, ids.map((i) => g[i][M.di]),
        ids.map((i) => `<b>${title(i)}</b><br>output gain ${pct(g[i].output_gain_pct)}<br>land saved ${fmt(g[i].land_saving_pct, 1)}%`),
        { height: 520, label: M.label, scale: M.scale });
    }
    plot("#chDist", [
      { type: "bar", orientation: "h", name: "Output gain % (Model 1)", y: d.map((x) => title(x.District)), x: d.map((x) => x.output_gain_pct), marker: { color: ACC } },
      { type: "bar", orientation: "h", name: "Land saved % (Model 2)", y: d.map((x) => title(x.District)), x: d.map((x) => x.land_saving_pct), marker: { color: SOIL } },
    ], { barmode: "group", xaxis: { title: "%" } }, Math.max(420, 22 * d.length + 80));
    plot("#chDistScatter", [{ type: "scatter", mode: "markers", x: d.map((x) => x.crops), y: d.map((x) => x[M.di]),
      text: d.map((x) => title(x.District)), marker: { color: M.hi, size: 10, opacity: 0.75, line: { color: "#fff", width: 1 } },
      hovertemplate: "%{text}<br>%{x} crops · %{y:+.1f}%<extra></extra>" }],
      { showlegend: false, xaxis: { title: "number of crops in the district's LP", dtick: 2 }, yaxis: { title: `${M.title.toLowerCase()} %` } }, 320);
  },
};
function draw(page) { if (S.r && CHARTS[page]) CHARTS[page](S.r); }

// ------------------------------------------------------------------ start
show(START);
(async () => {
  status("Loading the dataset (about 10 s the first time)…");
  try {
    S.meta = await api("/api/meta");
    S.seasons = S.meta.seasons; S.blocked = S.meta.blocked || {};
    const q = new URLSearchParams(location.search), st = usable(q.get("state")).length ? q.get("state") : S.meta.state;
    for (const [p, k] of [["land", "land_pct"], ["target", "target_pct"], ["band", "band_pct"], ["pulse", "pulse_share"]]) if (q.has(p)) S.set[k] = +q.get(p);
    if (["historical", "band"].includes(q.get("bounds"))) S.set.bounds = q.get("bounds");
    if (YIELD[q.get("yield")]) S.set.yield_method = q.get("yield");
    const ok = usable(st);
    fillSelects(st, ok.includes(q.get("season")) ? q.get("season") : ok.includes(S.meta.season) ? S.meta.season : ok[0]);
    await run();
  } catch (e) { status(e.message, true); }
})();
