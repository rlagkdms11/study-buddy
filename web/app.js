/* study-buddy 웹 화면
 * 화면은 주소 뒤 #으로 나눈다: #/upload → #/plan → #/today
 * 모든 기록은 이 브라우저(localStorage)에만 저장한다. 서버는 저장하지 않는다.
 */

// ---------- 저장 ----------
const STORE_KEY = "study-buddy:v1";

function load() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; }
  catch { return {}; }
}
function save(data) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(data)); }
  catch { alert("브라우저 저장 공간이 꽉 찼어요. 설정에서 지난 기록을 지워 주세요."); }
}
let store = load();
// store 모양: { files, pages, startDate, examDate, style, plan, days: { "1": { note, quiz, ... } } }

// ---------- 도구 ----------
const app = document.getElementById("app");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function ymd(d) {  // 내 컴퓨터 시간 기준 YYYY-MM-DD
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
function addDays(s, n) { const d = new Date(s + "T00:00"); d.setDate(d.getDate() + n); return ymd(d); }
function diffDays(a, b) { return Math.round((new Date(b + "T00:00") - new Date(a + "T00:00")) / 86400000); }
function md(s) { const [, m, d] = s.split("-"); return `${+m}/${d}`; }
function korDate(s) { const [, m, d] = s.split("-"); return `${+m}월 ${+d}일`; }

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = typeof body.detail === "string" ? body.detail : "요청을 처리하지 못했어요.";
    throw new Error(msg);
  }
  return body;
}
const postJSON = (path, data) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

const GEAR = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#5c6370" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/></svg>`;

function navHeader(current) {
  const tab = (href, name, key) => `<a href="${href}" ${current === key ? 'aria-current="page"' : ""}>${name}</a>`;
  return `<header class="top"><div class="bar">
    <span class="logo">study-buddy</span>
    <nav class="tabs" aria-label="메뉴">${tab("#/today", "오늘", "today")}${tab("#/history", "지난 공부", "history")}</nav>
    <a class="icon-btn" href="#/settings" aria-label="설정">${GEAR}</a>
  </div></header>`;
}

// ---------- ① 강의 자료 올리기 ----------
let chosenFiles = [];   // 고른 File 객체 (저장하지 않음)
let uploaded = null;    // 서버가 읽어 준 결과

function renderUpload() {
  app.innerHTML = `
  <header><div class="bar center"><span class="logo">study-buddy</span></div></header>
  <main style="max-width:560px">
    <div class="head"><span class="step">1 / 2</span><h1 class="title">시험 범위 강의 PDF를 올려 주세요</h1></div>
    <label class="drop" id="drop">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/></svg>
      <span style="font-weight:500">끌어다 놓거나 눌러서 고르기</span>
      <span class="hint">여러 개 가능</span>
      <input id="file" type="file" accept="application/pdf,.pdf" multiple>
    </label>
    <div id="files"></div>
    <div id="msg" role="status"></div>
    <button class="primary wide" id="next" disabled>다음</button>
  </main>`;

  const drop = document.getElementById("drop");
  document.getElementById("file").addEventListener("change", (e) => addFiles(e.target.files));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); addFiles(e.dataTransfer.files); });
  document.getElementById("next").addEventListener("click", () => {
    store = { files: uploaded.files, pages: uploaded.pages, days: {} };
    save(store);
    location.hash = "#/plan";
  });
  drawFiles();
}

function addFiles(list) {
  for (const f of list) {
    if (!f.name.toLowerCase().endsWith(".pdf")) continue;
    if (!chosenFiles.some((c) => c.name === f.name && c.size === f.size)) chosenFiles.push(f);
  }
  readFiles();
}

async function readFiles() {
  const msg = document.getElementById("msg");
  const next = document.getElementById("next");
  uploaded = null;
  next.disabled = true;
  if (!chosenFiles.length) { msg.innerHTML = ""; drawFiles(); return; }
  msg.innerHTML = `<span class="status"><span class="dot busy"></span>PDF 읽는 중…</span>`;
  const form = new FormData();
  chosenFiles.forEach((f) => form.append("files", f));
  try {
    uploaded = await api("/api/pdfs", { method: "POST", body: form });
    msg.innerHTML = uploaded.empty_pages.length
      ? `<span class="hint">글자가 없는 쪽이 ${uploaded.empty_pages.length}개 있어요 (그림만 있는 슬라이드). 그 쪽은 건너뛰어요.</span>`
      : "";
    next.disabled = false;
  } catch (e) {
    msg.innerHTML = `<p class="error">${esc(e.message)}</p>`;
  }
  drawFiles();
}

function drawFiles() {
  const box = document.getElementById("files");
  if (!chosenFiles.length) { box.innerHTML = ""; return; }
  // 서버가 읽어 줬으면 강의 순서와 쪽수를, 아니면 고른 순서를 보여 준다
  const shown = uploaded
    ? uploaded.files.map((f) => ({ name: f.name, info: `${f.pages}쪽` }))
    : chosenFiles.map((f) => ({ name: f.name.replace(/\.pdf$/i, ""), info: "" }));
  box.innerHTML = `<ul class="rows" aria-label="올린 자료">${shown.map((f) => `
    <li><span class="grow">${esc(f.name)}</span><span class="hint">${f.info}</span>
    <button class="x" data-name="${esc(f.name)}" aria-label="${esc(f.name)} 빼기">×</button></li>`).join("")}</ul>`;
  box.querySelectorAll(".x").forEach((b) => b.addEventListener("click", () => {
    chosenFiles = chosenFiles.filter((f) => f.name.replace(/\.pdf$/i, "") !== b.dataset.name);
    readFiles();
  }));
}

// ---------- ② 학습 계획 ----------
function renderPlan() {
  if (!store.pages) return redirect("#/upload");
  const today = ymd(new Date());
  const start = store.startDate || today;
  const exam = store.examDate || addDays(start, 7);
  const style = store.style || "hand";

  app.innerHTML = `
  <header><div class="bar split"><a href="#/upload" style="font-size:14px">← 이전</a><span class="logo">study-buddy</span><span style="width:40px"></span></div></header>
  <main>
    <div class="head"><span class="step">2 / 2</span><h1 class="title">시험일을 고르면 하루 분량을 나눠 드려요</h1></div>
    <section class="dates" aria-label="날짜">
      <label>공부 시작일<input type="date" id="start" value="${start}"></label>
      <label>시험일<input type="date" id="exam" value="${exam}"></label>
    </section>
    <section class="section" id="days" aria-live="polite"></section>
    <section class="section">
      <div class="head" style="gap:4px"><h2>정리본 스타일</h2><span class="hint">나중에 설정에서 바꿀 수 있어요</span></div>
      <div class="styles" role="radiogroup" aria-label="정리본 스타일">
        <label class="style-card">
          <div class="pv hand" aria-hidden="true"><span class="tape">1강</span><span class="hl">구성 요소 3가지</span><span class="u">Solution은 단계별 절차 아님</span><span class="why">↳ 왜? O/X 함정으로 자주 나와요</span></div>
          <span style="display:flex;gap:8px;align-items:center"><input type="radio" name="style" value="hand" ${style === "hand" ? "checked" : ""}><b>필기 스타일</b></span>
          <ul><li>밑줄 + 형광펜 = 시험에 나올 내용</li><li>빨간 손글씨 = 왜 중요한지</li><li>단원마다 테이프 라벨, 비유는 메모</li></ul>
          <small>시험 직전 훑어보기 좋아요</small>
        </label>
        <label class="style-card">
          <div class="pv clean" aria-hidden="true"><b>구성 요소 3가지</b><span class="bars"><span></span><span></span></span><span class="chips"><span></span><span></span><span></span></span></div>
          <span style="display:flex;gap:8px;align-items:center"><input type="radio" name="style" value="clean" ${style === "clean" ? "checked" : ""}><b>깔끔 스타일</b></span>
          <ul><li>개념마다 "왜 → 그래서" 카드</li><li>단서 · 비교는 표로 정리</li><li>분류는 색으로 구분</li></ul>
          <small>처음 배울 때 차근차근 읽기 좋아요</small>
        </label>
      </div>
    </section>
    <button class="primary wide" id="go" disabled>이 계획으로 시작하기</button>
  </main>`;

  let plan = null, showAll = false;
  const startEl = document.getElementById("start");
  const examEl = document.getElementById("exam");
  const goBtn = document.getElementById("go");

  function drawDays() {
    const box = document.getElementById("days");
    if (!plan) return;
    const per = Math.round(store.pages.length / plan.length);
    const list = showAll ? plan : plan.slice(0, 3);
    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <h2>${plan.length}일 · 하루 약 ${per}쪽</h2>
        ${plan.length > 3 ? `<button class="link" id="all" style="font-size:14px">${showAll ? "접기" : "전체 보기"}</button>` : ""}
      </div>
      <ol class="rows">${list.map((d) => `<li class="plan-row"><span class="when">Day ${d.day} · ${md(d.date)}</span><span>${esc(d.label)}</span></li>`).join("")}</ol>`;
    const all = document.getElementById("all");
    if (all) all.addEventListener("click", () => { showAll = !showAll; drawDays(); });
  }

  async function update() {
    goBtn.disabled = true;
    const box = document.getElementById("days");
    try {
      const res = await postJSON("/api/plan", {
        pages: store.pages.map(({ file, page }) => ({ file, page })),
        start_date: startEl.value, exam_date: examEl.value,
      });
      plan = res.days;
      drawDays();
      goBtn.disabled = false;
    } catch (e) {
      plan = null;
      box.innerHTML = `<p class="error">${esc(e.message)}</p>`;
    }
  }
  startEl.addEventListener("change", update);
  examEl.addEventListener("change", update);
  update();

  goBtn.addEventListener("click", () => {
    store.startDate = startEl.value;
    store.examDate = examEl.value;
    store.style = document.querySelector('input[name="style"]:checked').value;
    store.plan = plan;
    store.days = {};
    save(store);
    go("#/today");
  });
}

// ---------- ③ 오늘 ----------
function todayIndex() {
  const today = ymd(new Date());
  const i = store.plan.findIndex((d) => d.date === today);
  if (i >= 0) return i;
  return today < store.plan[0].date ? 0 : store.plan.length - 1;
}

function dayRecord(day) {
  return (store.days || {})[day] || {};
}

// 기다리는 사이에 다른 화면으로 가도 결과가 사라지지 않게, 저장된 최신 기록에 합쳐서 저장한다
function updateDay(day, patch) {
  store = load();
  store.days = store.days || {};
  store.days[day] = { ...(store.days[day] || {}), ...patch };
  save(store);
  return store.days[day];
}

function renderToday() {
  if (!store.plan) return redirect(store.pages ? "#/plan" : "#/upload");
  const today = ymd(new Date());
  const i = todayIndex();
  const d = store.plan[i];
  const dday = diffDays(today, store.examDate);
  const done = Object.values(store.days).filter((r) => r.quizDone).length;
  const before = today < store.plan[0].date;

  app.innerHTML = `${navHeader("today")}
  <main>
    <section class="section" style="gap:24px">
      <div class="head" style="gap:10px">
        <span class="meta">${korDate(today)} · Day ${d.day} / ${store.plan.length} · <b style="color:var(--accent)">D-${dday}</b></span>
        <h1 class="title big">${esc(d.label).replace(", ", ",<br>")}</h1>
        ${before ? `<span class="hint">${korDate(d.date)}부터 시작하는 범위예요</span>` : ""}
      </div>
      <div class="progress" role="progressbar" aria-label="학습 진행" aria-valuemin="0" aria-valuemax="${store.plan.length}" aria-valuenow="${done}"><div style="width:${(done / store.plan.length) * 100}%"></div></div>
      <div class="actions">
        <a class="primary" href="#/note/${d.day}">정리본 보기</a>
        <a href="#/quiz/${d.day}" style="font-size:16px;font-weight:500">퀴즈 풀기</a>
      </div>
      <div id="prep" class="status" aria-live="polite"></div>
    </section>
  </main>`;

  prepare(d);
}

// 오늘 화면을 열면 정리본 → 퀴즈 순서로 미리 만들어 둔다
const preparing = {};
async function prepare(d) {
  let rec = dayRecord(d.day);
  const show = (cls, text) => {
    const el = document.getElementById("prep");
    if (el) el.innerHTML = `<span class="dot ${cls}"></span>${text}`;
  };
  if (rec.note && rec.quiz) return show("ok", "정리본과 퀴즈가 준비됐어요");
  if (preparing[d.day]) return show("busy", "정리본과 퀴즈를 만드는 중이에요 · 1~2분");
  preparing[d.day] = true;
  const body = { pages: store.pages.slice(d.start - 1, d.end), first: d.start };
  try {
    if (!rec.note) {
      show("busy", "정리본을 만드는 중이에요 · 1~2분");
      const res = await postJSON("/api/note", body);
      rec = updateDay(d.day, { note: res.note, noteSeconds: res.elapsed });
    }
    if (!rec.quiz) {
      show("busy", "정리본 완성 · 퀴즈를 만드는 중이에요");
      const res = await postJSON("/api/quiz", { ...body, sections: rec.note.map || [] });
      rec = updateDay(d.day, { quiz: res.quiz, quizSeconds: res.elapsed });
    }
    show("ok", "정리본과 퀴즈가 준비됐어요");
  } catch (e) {
    show("bad", `${esc(e.message)} <button class="link" id="retry">다시 시도</button>`);
    const r = document.getElementById("retry");
    if (r) r.addEventListener("click", () => prepare(d));
  } finally {
    preparing[d.day] = false;
  }
}

// ---------- 아직 만들지 않은 화면 ----------
function renderSoon(name) {
  app.innerHTML = `${navHeader(name === "지난 공부" ? "history" : "")}
  <main><div class="head"><h1 class="title">${name}</h1><span class="hint">이 화면은 다음 단계에서 만들어요.</span></div>
  <a href="#/today">← 오늘로</a></main>`;
}

// ---------- 화면 고르기 ----------
function go(hash) { location.hash = hash; }
// 조건이 안 맞아 다른 화면으로 보낼 때는 뒤로 가기 기록을 남기지 않고 바로 그린다
function redirect(hash) { history.replaceState(null, "", hash); route(); }

function route() {
  store = load();
  const [, page, arg] = location.hash.split("/");
  window.scrollTo(0, 0);
  if (page === "upload") return renderUpload();
  if (page === "plan") return renderPlan();
  if (page === "today") return renderToday();
  if (page === "note") return renderSoon(`Day ${arg} 정리본`);
  if (page === "quiz") return renderSoon(`Day ${arg} 퀴즈`);
  if (page === "history") return renderSoon("지난 공부");
  if (page === "settings") return renderSoon("설정");
  redirect(store.plan ? "#/today" : "#/upload");
}
window.addEventListener("hashchange", route);
route();
