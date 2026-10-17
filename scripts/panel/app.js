"use strict";
const T = document.querySelector('meta[name="panel-token"]').content;
const KINDS = [["grid", "Portada"], ["wide", "Banner"], ["hero", "Fondo"], ["logo", "Logo"], ["icon", "Icono"]];
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const gb = b => (b / 1073741824).toFixed(b >= 1073741824 * 10 ? 0 : 1) + " GB";
const art = (id, k) => `/art/${id}/${k}?t=${T}&v=${artVer}`;

let state = {games: []}, cur = null, sgGame = null, kind = "grid", artVer = Date.now(), filterText = "", queryText = "";

function toast(msg, err = false) {
  const el = document.createElement("div");
  el.className = "toast" + (err ? " err" : "");
  el.textContent = msg;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), err ? 6000 : 3500);
}

async function api(path, opt = {}) {
  const r = await fetch(path + (path.includes("?") ? "&" : "?") + "t=" + T,
    {headers: {"X-Token": T, "Content-Type": "application/json"}, ...opt});
  const j = await r.json();
  if (!r.ok || j.error) throw new Error(j.error || r.status);
  return j;
}
const post = (path, body) => api(path, {method: "POST", body: JSON.stringify(body)});

/* ---------- barra de estado ---------- */
function pill(cls, html) { return `<span class="pill ${cls}"><i></i>${html}</span>`; }
async function refreshStatus() {
  try {
    const s = await api("/api/status");
    const g = s.gpu;
    state.steam_running = s.steam_running;
    $("#pills").innerHTML = [
      pill(s.mode_on ? "ok" : "", s.mode_on ? "Modo Domi <b>activo</b>" : "Modo Domi <b>apagado</b>"),
      pill(state.steam_running ? "warn" : "", state.steam_running ? "Steam de Domi <b>abierto</b>" : "Steam de Domi <b>cerrado</b>"),
      g ? pill("", `GPU <b>${esc(g.util)}%</b> · VRAM <b>${esc(g.vram)}</b>/${esc(g.vram_total)} MB · <b>${esc(g.watts)}</b> W`) : "",
      pill("", `RAM libre <b>${(s.ram_free_mb / 1024).toFixed(1)}</b> GB`),
      state.disk_free != null ? pill("", `Disco libre <b>${gb(state.disk_free)}</b>`) : "",
    ].join("");
  } catch (e) { /* estado no crítico */ }
}

/* ---------- biblioteca ---------- */
function renderLibrary() {
  const q = filterText.toLowerCase();
  const list = state.games.filter(g => g.name.toLowerCase().includes(q));
  $("#count").textContent = `${list.length} juego${list.length === 1 ? "" : "s"}`;
  $("#games").innerHTML = list.map(g => `
    <button class="cover ${cur && cur.appid === g.appid ? "sel" : ""}" role="listitem" data-id="${g.appid}">
      <div class="img" style="${g.art.grid ? `background-image:url('${art(g.appid, "grid")}')` : ""}">
        ${g.art.grid ? "" : `<div class="ph">${esc(g.name)}</div>`}
        ${g.in_steam ? "" : '<span class="tag">pendiente</span>'}
      </div>
      <div class="cap">${esc(g.name)}</div><div class="sub">${gb(g.size)}</div>
    </button>`).join("") || '<p class="muted">Sin juegos no-Steam.</p>';
}

async function load() {
  state = await api("/api/games");
  $("#exe").innerHTML = state.exes.map(e => `<option>${esc(e)}</option>`).join("");
  $("#exe").onchange();
  renderLibrary();
  refreshStatus();
  if (!state.has_key) toast("Falta la API key de SteamGridDB", true);
}

/* ---------- detalle ---------- */
function artRowHTML() {
  return KINDS.map(([k, l]) => `
    <figure>${cur.art[k]
      ? `<img src="${art(cur.appid, k)}" alt="${l}" style="height:${k === "grid" ? 150 : k === "icon" ? 64 : 90}px">`
      : `<div class="none" style="width:${k === "grid" ? 100 : 160}px;height:${k === "grid" ? 150 : 90}px">sin ${l.toLowerCase()}</div>`}
      <figcaption>${l}</figcaption></figure>`).join("");
}

// Solo actualiza fondo y artwork actual: el buscador, el juego elegido y la pestaña se conservan.
function renderArt() {
  if (!cur) return;
  const hero = $("#hero");
  hero.style.backgroundImage = cur.art.hero ? `url('${art(cur.appid, "hero")}')` : "";
  $("#art-current").innerHTML = artRowHTML();
}

function renderDetail() {
  if (!cur) return;
  $("#detail").innerHTML = `
    <div class="hero" id="hero"><h2>${esc(cur.name)}</h2>
      <div class="meta">${esc(cur.exe)} · appid ${cur.appid}</div></div>
    <div class="body">
      <div class="card"><h3>Artwork actual</h3><div class="art-row" id="art-current"></div></div>

      <div class="card"><h3>Cambiar artwork · SteamGridDB</h3>
        <p class="muted" style="margin:0 0 10px">Busca con el nombre que quieras: no tiene que coincidir con el del juego. Puedes aplicar varios assets seguidos.</p>
        <div class="row"><input id="q" class="grow" aria-label="Buscar en SteamGridDB">
          <button class="btn" id="do-search">Buscar</button></div>
        <div class="row" id="results" style="margin-top:10px"></div><div id="picker"></div></div>

      <div class="card"><h3>Nombre en Steam</h3>
        <div class="row"><input id="newname" class="grow" value="${esc(cur.name)}" aria-label="Nombre en Steam">
          <button class="btn" data-act="rename">Renombrar</button></div>
        <p class="muted" style="margin:8px 0 0">Mantiene portadas y partidas. Requiere el Steam de Domi cerrado.</p></div>

      <div class="card"><h3>Administrar</h3>
        <div class="row"><span class="muted">Juego <b>${gb(cur.size)}</b> · Partidas/prefijo <b>${gb(cur.saves)}</b></span>
          <span class="grow"></span>
          <label class="muted"><input type="checkbox" id="delsaves"> borrar también partidas</label>
          <button class="btn" data-act="unlink">Quitar de Steam</button>
          <button class="btn danger" data-act="delete">Eliminar y liberar ${gb(cur.size)}</button></div>
        ${state.steam_running ? '<p class="muted" style="margin:10px 0 0">El Steam de Domi está abierto: ciérralo (Quit app en Moonlight) para quitar o renombrar juegos.</p>' : ""}
      </div>
    </div>`;
  $("#q").value = queryText;
  $("#q").oninput = e => { queryText = e.target.value; };
  $("#q").onkeydown = e => { if (e.key === "Enter") search($("#q").value, true); };
  $("#do-search").onclick = () => search($("#q").value, true);
  renderArt();
}

async function pick(appid) {
  cur = state.games.find(g => g.appid === appid);
  sgGame = null;
  queryText = cur ? cur.name : "";
  renderLibrary(); renderDetail();
  if (cur) search(queryText, true);
  window.scrollTo({top: 0});
}

async function search(q, reset = false) {
  if (reset) sgGame = null;
  $("#results").innerHTML = '<span class="muted">Buscando…</span>';
  try {
    const r = await api("/api/search?q=" + encodeURIComponent(q));
    $("#results").innerHTML = r.map(g => `<button class="btn ${sgGame === g.id ? "on" : ""}" data-sg="${g.id}">${esc(g.name)}${g.year ? " (" + new Date(g.year * 1000).getFullYear() + ")" : ""}</button>`).join("")
      || '<span class="muted">Sin resultados</span>';
    if (sgGame && r.some(g => g.id === sgGame)) chooseGame(sgGame);
    else if (r[0]) chooseGame(r[0].id);
  } catch (e) { $("#results").textContent = e.message; }
}

function chooseGame(id) {
  sgGame = id;
  document.querySelectorAll("#results [data-sg]").forEach(b => b.classList.toggle("on", +b.dataset.sg === id));
  $("#picker").innerHTML = `<div class="tabs">${KINDS.map(([k, l]) => `<button class="btn ${k === kind ? "on" : ""}" data-k="${k}">${l}</button>`).join("")}
    <span style="flex:1"></span><button class="btn" id="do-steam" title="Aplica los assets oficiales de la tienda de Steam que existan">Originales de Steam</button> <button class="btn pri" id="do-auto">✨ Auto: lo mejor de todo</button></div><div id="tiles"></div>`;
  showKind();
}

async function showKind() {
  const el = $("#tiles");
  el.className = "grid"; el.innerHTML = '<div class="skeleton"></div>'.repeat(4);
  try {
    const a = await api(`/api/assets?game=${sgGame}&kind=${kind}`);
    el.className = "grid" + (["wide", "hero", "logo"].includes(kind) ? " wide" : "");
    el.innerHTML = a.map(x => `<button class="tile" data-url="${esc(x.url)}"><img loading="lazy" src="${esc(x.thumb)}" alt=""><small>${x.width ? esc(x.width) + "×" + esc(x.height) + " · " : ""}${esc(x.style || "")}</small></button>`).join("")
      || '<span class="muted">No hay imágenes de este tipo.</span>';
  } catch (e) { el.className = "muted"; el.textContent = e.message; }
}

async function refreshKeep() {
  artVer = Date.now();
  await load();
  cur = state.games.find(g => g.appid === cur?.appid) || null;
  renderArt();   // el buscador, el juego elegido y la pestaña no se tocan
}

async function renameGame() {
  const name = $("#newname").value.trim();
  if (!name || name === cur.name) return;
  if (!confirm(`¿Renombrar «${cur.name}» a «${name}»? Se conservan portadas y partidas.`)) return;
  const r = await post("/api/rename", {appid: cur.appid, name});
  artVer = Date.now();
  await load();
  cur = state.games.find(g => g.appid === r.appid) || null;
  toast("Renombrado ✔");
  renderLibrary(); renderDetail();
  if (cur) search(queryText, false);
}

async function removeGame(files) {
  const saves = $("#delsaves").checked;
  const msg = files ? `¿Eliminar «${cur.name}» del disco (${gb(cur.size)})${saves ? " y sus partidas guardadas" : ""}?`
                    : `¿Quitar «${cur.name}» de Steam? Los archivos se conservan en /srv/juegos.`;
  if (!confirm(msg)) return;
  try {
    const r = await post("/api/remove", {appid: cur.appid, files, saves});
    toast(r.log.join(" · "));
    cur = null; sgGame = null;
    $("#detail").innerHTML = document.querySelector(".empty")?.outerHTML || "";
    location.reload();
  } catch (e) { toast(e.message, true); }
}

/* ---------- eventos (delegación; sin onclick inline) ---------- */
document.addEventListener("click", async e => {
  const t = e.target.closest("[data-id],[data-sg],[data-k],[data-url],[data-act],#do-auto,#do-steam");
  if (!t) return;
  try {
    if (t.dataset.id) return pick(+t.dataset.id);
    if (t.dataset.sg) return chooseGame(+t.dataset.sg);
    if (t.dataset.k) { kind = t.dataset.k; document.querySelectorAll("[data-k]").forEach(b => b.classList.toggle("on", b.dataset.k === kind)); return showKind(); }
    if (t.dataset.url) {
      const r = await post("/api/apply", {appid: cur.appid, kind, url: t.dataset.url});
      toast(r.note || "Aplicado ✔"); return refreshKeep();
    }
    if (t.id === "do-steam") {
      toast("Buscando los originales de Steam…");
      const r = await post("/api/steam-originals", {appid: cur.appid, game: sgGame});
      const got = Object.keys(r.applied);
      toast(got.length ? "Originales de Steam aplicados: " + got.join(", ") + (r.missing.length ? ` (sin original: ${r.missing.join(", ")})` : "")
                       : "Este juego no tiene assets originales en Steam", !got.length);
      return refreshKeep();
    }
    if (t.id === "do-auto") {
      toast("Aplicando lo mejor de cada tipo…");
      const r = await post("/api/auto", {appid: cur.appid, game: sgGame});
      toast("Aplicado: " + Object.keys(r.applied).join(", ")); return refreshKeep();
    }
    if (t.dataset.act === "rename") return await renameGame();
    if (t.dataset.act === "unlink") return removeGame(false);
    if (t.dataset.act === "delete") return removeGame(true);
  } catch (err) { toast("Error: " + err.message, true); }
});

$("#filter").oninput = e => { filterText = e.target.value; renderLibrary(); };
$("#btn-add").onclick = () => { $("#dlg-add").returnValue = ""; $("#dlg-add").showModal(); };
$("#exe").onchange = () => { $("#name").value = $("#exe").value.split("/").slice(-2, -1)[0] || ""; };
$("#dlg-add").addEventListener("close", async () => {
  if ($("#dlg-add").returnValue !== "default") return;
  try {
    const r = await post("/api/add", {exe: $("#exe").value, name: $("#name").value});
    toast("Añadido ✔"); await load(); pick(r.appid);
  } catch (e) { toast(e.message, true); }
});

load();
setInterval(refreshStatus, 5000);
