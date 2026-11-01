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
  let res;
  try {
    res = await fetch(path, options);
  } catch {
    throw new Error("서버에 연결하지 못했어요. 터미널에서 서버가 켜져 있는지 확인해 주세요.");
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = typeof body.detail === "string" ? body.detail : "요청을 처리하지 못했어요.";
    throw new Error(msg);
  }
  return body;
}
const postJSON = (path, data) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

const GEAR = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#5c6370" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/></svg>`;

function navHeader(current, wide = false) {
  const tab = (href, name, key) => `<a href="${href}" ${current === key ? 'aria-current="page"' : ""}>${name}</a>`;
  return `<header class="top"><div class="bar${wide ? " wide" : ""}">
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
  <header class="top"><div class="bar wide"><span class="logo">study-buddy</span></div></header>
  <main class="wide two-col">
    <div class="intro">
      <span class="step">1 / 2</span>
      <h1 class="title hero">시험 범위 강의 PDF를<br>올려 주세요</h1>
      <p class="lede">올린 자료로 시험일까지 공부 범위를 나누고, 매일 그날 범위로 정리본과 퀴즈를 만들어 드려요.</p>
      <ol class="howto">
        <li><b>강의 PDF 올리기</b><span>여러 파일이면 강의 순서대로 알아서 정렬해요</span></li>
        <li><b>시험일 고르기</b><span>남은 날에 맞춰 하루 분량을 나눠요</span></li>
        <li><b>매일 정리본 읽고 퀴즈 풀기</b><span>틀린 문제는 복습 날에 다시 나와요</span></li>
      </ol>
      <p class="hint">자료는 정리본을 만들 때만 쓰고 서버에 저장하지 않아요.</p>
    </div>
    <div class="panel">
      <label class="drop tall" id="drop">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/></svg>
        <span style="font-weight:500;font-size:17px">끌어다 놓거나 눌러서 고르기</span>
        <span class="hint">PDF · 여러 개 가능</span>
        <input id="file" type="file" accept="application/pdf,.pdf" multiple>
      </label>
      <div id="files"></div>
      <div id="msg" role="status"></div>
      <button class="primary wide" id="next" disabled>다음</button>
    </div>
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
  <header class="top"><div class="bar wide split"><span class="logo">study-buddy</span><a href="#/upload" style="font-size:14px">← 자료 다시 고르기</a></div></header>
  <main class="wide">
    <div class="head"><span class="step">2 / 2</span><h1 class="title hero">시험일을 고르면 하루 분량을 나눠 드려요</h1></div>
    <div class="plan-grid">
      <div class="plan-main">
        <section class="dates" aria-label="날짜">
          <label>공부 시작일<input type="date" id="start" value="${start}"></label>
          <label>시험일<input type="date" id="exam" value="${exam}"></label>
        </section>
        <section class="section" id="days" aria-live="polite"></section>
      </div>
      <aside class="plan-side">
        <div class="head" style="gap:4px"><h2 style="font-size:17px">정리본 스타일</h2><span class="hint">나중에 설정에서 바꿀 수 있어요</span></div>
        <div class="styles stack" role="radiogroup" aria-label="정리본 스타일">
          <label class="style-card">
            <div class="pv hand" aria-hidden="true"><span class="tape">1강</span><span class="hl">구성 요소 3가지</span><span class="u">Solution은 단계별 절차 아님</span><span class="why">↳ 왜? O/X 함정 단골!</span></div>
            <div class="card-text">
              <span style="display:flex;gap:8px;align-items:center"><input type="radio" name="style" value="hand" ${style === "hand" ? "checked" : ""}><b>필기 스타일</b></span>
              <ul><li>밑줄 + 형광펜 = 시험에 나올 내용</li><li>빨간 손글씨 = 왜 중요한지</li><li>단원마다 테이프 라벨, 비유는 메모</li></ul>
              <small>시험 직전 훑어보기 좋아요</small>
            </div>
          </label>
          <label class="style-card">
            <div class="pv clean" aria-hidden="true"><b>구성 요소 3가지</b><span class="bars"><span></span><span></span></span><span class="chips"><span></span><span></span><span></span></span></div>
            <div class="card-text">
              <span style="display:flex;gap:8px;align-items:center"><input type="radio" name="style" value="clean" ${style === "clean" ? "checked" : ""}><b>깔끔 스타일</b></span>
              <ul><li>개념마다 "왜 → 그래서" 카드</li><li>단서 · 비교는 표로 정리</li><li>분류는 색으로 구분</li></ul>
              <small>처음 배울 때 차근차근 읽기 좋아요</small>
            </div>
          </label>
        </div>
        <button class="primary wide" id="go" disabled>이 계획으로 시작하기</button>
      </aside>
    </div>
  </main>`;

  let plan = null, showAll = false, finalDate = null;
  const startEl = document.getElementById("start");
  const examEl = document.getElementById("exam");
  const goBtn = document.getElementById("go");

  function drawDays() {
    const box = document.getElementById("days");
    if (!plan) return;
    const per = Math.round(store.pages.length / plan.length);
    const list = showAll ? plan : plan.slice(0, 7);
    box.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <h2>${plan.length}일 · 하루 약 ${per}쪽</h2>
        ${plan.length > 7 ? `<button class="link" id="all" style="font-size:14px">${showAll ? "접기" : `전체 ${plan.length}일 보기`}</button>` : ""}
      </div>
      <ol class="rows">${list.map((d) => `<li class="plan-row"><span class="when">Day ${d.day} · ${md(d.date)}</span><span>${esc(d.label)}</span></li>`).join("")}
      ${finalDate && (showAll || plan.length <= 7) ? `<li class="plan-row"><span class="when">총정리 · ${md(finalDate)}</span><span><b>시험 전날</b> · 전체 요약본 + 전체 범위 퀴즈</span></li>` : ""}</ol>
      ${finalDate ? `<p class="hint" style="margin:8px 0 0">시험 전날(${korDate(finalDate)})은 새 범위 없이 전체를 총정리해요</p>` : ""}`;
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
      finalDate = res.final_date || null;
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
    store.finalDate = finalDate;
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
  if (store.examDate && today >= finalDay()) return renderFinalToday(today);
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
    ${reviewSectionHTML(today)}
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

// ---------- ④ 정리본 (필기 스타일) ----------
const TAPES = ["#ffd3de", "#c8f0df", "#d3e4ff"];

// 전체 쪽 번호를 "p.3" 또는 여러 강의가 섞이면 "1강 p.3"처럼 바꾼다
function lectureShort(name) {
  const m = name.match(/^[\d\-~]+강/);
  return m ? m[0] : name;
}
function pageRange(nums, multi) {
  const list = (nums || []).map((n) => store.pages[n - 1]).filter(Boolean);
  if (!list.length) return "";
  const a = list[0], b = list[list.length - 1];
  const prefix = multi ? `${lectureShort(a.file)} ` : "";
  if (a.file !== b.file) return `${lectureShort(a.file)} p.${a.page} – ${lectureShort(b.file)} p.${b.page}`;
  return a.page === b.page ? `${prefix}p.${a.page}` : `${prefix}p.${a.page}–${b.page}`;
}
const stars = (n) => "★".repeat(Math.max(0, Math.min(3, +n || 0)));
const arr = (x) => (Array.isArray(x) ? x : []);

function renderNote(day, jump) {
  if (!store.plan) return redirect("#/upload");
  const d = store.plan.find((p) => String(p.day) === String(day));
  if (!d) return redirect("#/today");
  const rec = dayRecord(d.day);
  const note = rec.note;
  const multi = new Set(store.pages.slice(d.start - 1, d.end).map((p) => p.file)).size > 1;

  if (!note) {
    app.innerHTML = `${navHeader("")}
    <main><div class="head"><span class="meta">Day ${d.day} · ${esc(d.label)}</span><h1 class="title">정리본을 아직 만들지 않았어요</h1>
    <span class="hint">오늘 화면을 열면 자동으로 만들기 시작해요.</span></div>
    <div class="actions"><a class="primary" href="#/today">오늘로 가서 만들기</a></div></main>`;
    return;
  }

  const sections = arr(note.sections);
  const top = sections.flatMap((s) => arr(s.key_points).filter((k) => +k.importance >= 3).map((k) => k.text)).slice(0, 5);
  const comps = arr(note.review && note.review.comparisons);

  const sectionHTML = (s, i) => {
    const pts = arr(s.key_points), traps = arr(s.traps), clues = arr(s.clues);
    return `
    <section class="paper unit" id="s${i}">
      ${pageRange(s.pages, multi) ? `<span class="tape" style="background:${TAPES[i % 3]}">${esc(pageRange(s.pages, multi))}</span>` : ""}
      <h2>${esc(s.title)}${s.importance ? `<span class="stars" aria-label="중요도 ${+s.importance}">${stars(s.importance)}</span>` : ""}</h2>
      ${s.link ? `<p class="lead">${esc(s.link)}</p>` : ""}
      ${s.why || s.so ? `<div class="flow">${s.why ? `왜? ${esc(s.why)}` : ""}${s.why && s.so ? " → " : ""}${s.so ? `그래서 ${esc(s.so)}` : ""}</div>` : ""}
      ${pts.length ? `<h3><b style="background:linear-gradient(transparent 55%, ${TAPES[(i + 1) % 3]} 55%)">꼭 외울 것</b></h3>
        <ul>${pts.map((k) => `<li>${+k.importance >= 2 ? `<span class="u">${esc(k.text)}</span>` : esc(k.text)}</li>`).join("")}</ul>` : ""}
      ${traps.length ? traps.map((t) => `<span class="red">↳ 주의! ${esc(t.text)}</span>`).join("") : ""}
      ${clues.length ? `<h3><b style="background:linear-gradient(transparent 55%, ${TAPES[(i + 2) % 3]} 55%)">이런 말이 보이면</b></h3>
        <div class="tbl"><table><tr><th>문제에 이런 문장이 보이면</th><th>답</th></tr>
        ${clues.map((c) => `<tr><td>${esc(c.clue)}</td><td>${esc(c.answer)}</td></tr>`).join("")}</table></div>` : ""}
      ${s.definition ? `<h3><b style="background:linear-gradient(transparent 55%, #ffd3de 55%)">서술형 한 문장</b></h3><p><span class="u">${esc(s.definition)}</span></p>` : ""}
      ${s.analogy ? `<div class="memo">비유 (자료 밖 설명) · ${esc(s.analogy)}</div>` : ""}
      ${s.check && s.check.q ? `<div style="margin-top:12px">
        <button type="button" class="hand-btn" data-check="${i}" aria-expanded="false">확인 질문 보기</button>
        <div class="check-a" id="c${i}" hidden><b>Q.</b> ${esc(s.check.q)}<span class="red">A. ${esc(s.check.a)}</span></div></div>` : ""}
    </section>`;
  };

  app.innerHTML = `<div class="note-page"><div class="note-wrap">
    <div class="note-top">
      <span class="muted">Day ${d.day} · ${esc(d.label)}</span>
      <span style="display:flex;gap:8px;align-items:center"><a href="#/today" style="padding:10px 6px">← 오늘로</a><a class="pill" href="#/quiz/${d.day}">퀴즈 풀기 ✎</a></span>
    </div>
    <header class="paper note-head">
      <div class="sub">Day ${d.day} · ${md(d.date)}</div>
      <h1><span>${esc(note.title || "정리 노트")}</span></h1>
      <p>${esc(d.label)} (${d.count}쪽)을 강의 순서대로 정리했어요. 자료에 있는 내용만 담았어요.</p>
      <div class="legend">
        <div><span class="u">밑줄 + 형광펜</span> = 시험에 나올 확률 높음</div>
        <div><span class="hand" style="font-size:18px;color:#d93a55">빨간 손글씨</span> = 틀리기 쉬운 점</div>
        <div><span class="src" style="margin:0">p.3</span> = 슬라이드 번호</div>
      </div>
    </header>
    <nav class="note-chips" aria-label="단원 바로가기">
      ${sections.map((s, i) => `<a href="#s${i}" data-jump="s${i}">${i + 1} ${esc(s.title)}</a>`).join("")}
      ${top.length ? `<a href="#top" data-jump="top">꼭 외울 것</a>` : ""}
      ${comps.length ? `<a href="#cmp" data-jump="cmp">헷갈리는 쌍</a>` : ""}
    </nav>
    ${sections.map(sectionHTML).join("")}
    ${top.length ? `<section class="paper unit" id="top"><span class="tape" style="background:#d3e4ff">꼭 외울 것</span>
      <h2>시험 직전 TOP ${top.length}</h2><ol>${top.map((t) => `<li>${esc(t)}</li>`).join("")}</ol></section>` : ""}
    ${comps.length ? `<section class="paper unit" id="cmp"><span class="tape" style="background:#ffd3de">헷갈리는 쌍</span>
      ${comps.map((c) => `<h3>${esc(c.title)}</h3><div class="tbl"><table>
        <tr>${arr(c.header).map((h) => `<th>${esc(h)}</th>`).join("")}</tr>
        ${arr(c.rows).map((r) => `<tr>${arr(r).map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</table></div>`).join("")}</section>` : ""}
    <div class="note-end">
      <span class="hand" style="font-size:22px;color:#5d6880">다 읽었으면 바로 확인해 봐요!</span>
      <a class="big-quiz" href="#/quiz/${d.day}">이 범위 퀴즈 풀기 →</a>
    </div>
  </div></div>`;

  // 단원 바로가기: 주소(#/note/1)를 바꾸지 않고 그 단원으로 스크롤
  app.querySelectorAll("[data-jump]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    document.getElementById(a.dataset.jump).scrollIntoView({ behavior: "smooth" });
  }));
  if (jump && document.getElementById(jump)) {
    const target = document.getElementById(jump);
    requestAnimationFrame(() => target.scrollIntoView());
    target.style.outline = "3px solid #fff08a";
    setTimeout(() => (target.style.outline = ""), 2000);
  }
  app.querySelectorAll("[data-check]").forEach((b) => b.addEventListener("click", () => {
    const box = document.getElementById("c" + b.dataset.check);
    box.hidden = !box.hidden;
    b.setAttribute("aria-expanded", String(!box.hidden));
    b.textContent = box.hidden ? "확인 질문 보기" : "확인 질문 접기";
  }));
}

// ---------- ⑥ 퀴즈 ----------
// 단답형 채점: 띄어쓰기·대소문자·기호를 무시하고 비교한다
function normalize(t) {
  return String(t ?? "").toLowerCase().replace(/[\s.,()[\]"'`·:;!?\-_/{}<>]/g, "");
}
function isCorrect(q, answer) {
  if (answer === undefined || answer === null || answer === "") return false;
  if (q.type === "short") {
    const a = normalize(answer), b = normalize(q.answer_text);
    return !!a && (a === b || (a.length >= 2 && b.includes(a) && a.length >= b.length / 2));
  }
  return +answer === +q.answer_index;
}

function renderQuiz(day) {
  if (!store.plan) return redirect("#/upload");
  const d = store.plan.find((p) => String(p.day) === String(day));
  if (!d) return redirect("#/today");
  const rec = dayRecord(d.day);
  const qs = arr(rec.quiz && rec.quiz.questions);
  const multi = new Set(store.pages.slice(d.start - 1, d.end).map((p) => p.file)).size > 1;
  const sectionTitles = arr(rec.note && rec.note.sections).map((s) => s.title);

  if (!qs.length) {
    app.innerHTML = `${navHeader("")}
    <main><div class="head"><span class="meta">Day ${d.day} · ${esc(d.label)}</span><h1 class="title">퀴즈를 아직 만들지 않았어요</h1>
    <span class="hint">오늘 화면을 열면 정리본 다음에 자동으로 만들어요.</span></div>
    <div class="actions"><a class="primary" href="#/today">오늘로 가서 만들기</a></div></main>`;
    return;
  }

  const answers = rec.answers || {};
  const graded = !!rec.graded;
  const only = Array.isArray(rec.only) ? rec.only : null;   // 틀린 문제 다시 풀기일 때 그 번호만
  const shown = qs.map((q, i) => i).filter((i) => !only || only.includes(i));
  const flags = rec.flags || {};
  const overrides = rec.overrides || {};                  // 단답형을 "맞은 걸로" 바꾼 번호
  const right = (i) => overrides[i] || isCorrect(qs[i], answers[i]);
  const score = shown.filter(right).length;

  const optionHTML = (q, i) => {
    if (q.type === "short") {
      if (!graded) return `<input class="short" data-i="${i}" value="${esc(answers[i] || "")}" placeholder="답을 적어 주세요" aria-label="Q${i + 1} 답">`;
      return `<p class="short-result">내 답 <b class="${right(i) ? "ok" : "bad"}">${esc(answers[i] || "(안 씀)")}</b> · 정답 <b>${esc(q.answer_text)}</b>
        ${!right(i) && answers[i] ? `<button type="button" class="link muted" data-override="${i}" style="font-size:13px;margin-left:8px">맞은 걸로 할게요</button>` : ""}</p>`;
    }
    return `<ol class="opts" role="radiogroup" aria-label="Q${i + 1} 보기">${arr(q.options).map((o, k) => {
      const n = k + 1;
      const mine = +answers[i] === n, correct = +q.answer_index === n;
      if (!graded) {
        return `<li><label class="opt ${mine ? "picked" : ""}"><input type="radio" name="q${i}" value="${n}" ${mine ? "checked" : ""} data-i="${i}"><span class="n">${n}</span><span>${esc(o)}</span></label></li>`;
      }
      const cls = correct ? "ok" : mine ? "bad" : "";
      const tag = correct ? "정답" : mine ? "내 답" : "";
      return `<li class="opt done ${cls}"><span class="n">${n}</span><span class="grow">${esc(o)}</span>${tag ? `<span class="tag">${tag}</span>` : ""}</li>`;
    }).join("")}</ol>`;
  };

  const sectionLink = (q) => {
    const k = sectionTitles.indexOf(q.section);
    return k >= 0 ? `#/note/${d.day}/s${k}` : `#/note/${d.day}`;
  };

  const questionHTML = (i, no) => {
    const q = qs[i];
    const where = [q.section, pageRange(q.pages, multi)].filter(Boolean).map(esc).join(" · ");
    return `<article class="q ${graded ? (right(i) ? "is-ok" : "is-bad") : ""}" id="q${i}">
      <span class="meta">Q${no}${where ? ` · ${where}` : ""}${graded ? ` · <b class="${right(i) ? "ok" : "bad"}">${right(i) ? "맞음" : "틀림"}</b>` : ""}</span>
      <h2>${esc(q.question)}</h2>
      ${q.code ? `<pre class="code">${esc(q.code)}</pre>` : ""}
      ${optionHTML(q, i)}
      ${graded ? `<div class="explain-box">
        ${q.explanation ? `<span class="explain-label">해설</span><p class="explain">${esc(q.explanation)}</p>` : ""}
        <div class="explain-foot">
          <a class="see-note" href="${sectionLink(q)}">정리본${pageRange(q.pages, multi) ? ` ${esc(pageRange(q.pages, multi))}` : ""}에서 다시 보기 →</a>
          <span class="chips-right">
            <!-- "이해 안 돼요"는 #4 설명 기능을 만들 때 다시 넣는다 (지금은 눌러도 하는 일이 없어서 숨김) -->
            <button type="button" class="chip ${flags[i] === "wrong" ? "on" : ""}" data-flag="${i}" data-kind="wrong" aria-pressed="${flags[i] === "wrong"}">${flags[i] === "wrong" ? "✓ 신고함" : "정답이 이상해요"}</button>
          </span>
        </div>
      </div>` : ""}
    </article>`;
  };

  const wrongCount = shown.length - score;
  app.innerHTML = `
  <header><div class="bar split"><a href="#/today" style="font-size:14px">← 오늘로</a><a href="#/note/${d.day}" style="font-size:14px">정리본</a></div></header>
  <main>
    <div class="head" style="gap:6px">
      <span class="meta">Day ${d.day} · ${esc(d.label)}${only ? " · 틀린 문제 다시 풀기" : ""}</span>
      ${graded
        ? `<h1 class="title">${shown.length}문제 중 ${score}개 맞았어요</h1>
           <span class="hint">${wrongCount ? `틀린 ${wrongCount}문제는 지난 공부와 복습 날에 다시 나와요` : "다 맞았어요! 🎉"}</span>`
        : `<h1 class="title">${only ? `틀린 ${shown.length}문제 다시 풀기` : `퀴즈 ${shown.length}문제`}</h1>
           <span class="hint" id="left"></span>`}
    </div>
    ${shown.map((i, n) => questionHTML(i, n + 1)).join("")}
    <div class="actions ruled">
      ${graded
        ? `${wrongCount ? `<button class="primary" id="retry">틀린 문제 다시 풀기</button>` : `<a class="primary" href="#/today">오늘로 돌아가기</a>`}
           <button class="link" id="fresh">새 퀴즈 만들기</button>`
        : `<button class="primary" id="grade">채점하기</button>`}
      <span id="qmsg" class="status" aria-live="polite"></span>
    </div>
  </main>`;

  // 푸는 중: 고를 때마다 저장
  const saveAnswer = (i, v) => {
    const cur = dayRecord(d.day).answers || {};
    updateDay(d.day, { answers: { ...cur, [i]: v } });
    store = load();
    countLeft();
  };
  const countLeft = () => {
    const el = document.getElementById("left");
    if (!el) return;
    const a = dayRecord(d.day).answers || {};
    const left = shown.filter((i) => a[i] === undefined || a[i] === "").length;
    el.textContent = left ? `${left}문제 남았어요 · 고른 답은 바로 저장돼요` : "다 풀었어요. 채점해 볼까요?";
  };
  countLeft();
  app.querySelectorAll('input[type="radio"][data-i]').forEach((r) => r.addEventListener("change", () => {
    r.closest(".opts").querySelectorAll(".opt").forEach((l) => l.classList.remove("picked"));
    r.closest(".opt").classList.add("picked");
    saveAnswer(r.dataset.i, +r.value);
  }));
  app.querySelectorAll("input.short").forEach((t) => t.addEventListener("input", () => saveAnswer(t.dataset.i, t.value.trim())));

  const grade = document.getElementById("grade");
  if (grade) grade.addEventListener("click", () => {
    const a = dayRecord(d.day).answers || {};
    const left = shown.filter((i) => a[i] === undefined || a[i] === "").length;
    if (left) {
      const msg = document.getElementById("qmsg");
      if (grade.dataset.sure !== "1") {
        msg.textContent = `아직 ${left}문제를 안 풀었어요. 그대로 채점하려면 한 번 더 눌러 주세요.`;
        grade.dataset.sure = "1";
        return;
      }
    }
    const ov = dayRecord(d.day).overrides || {};
    const wrong = qs.map((q, i) => i).filter((i) => !(ov[i] || isCorrect(qs[i], a[i])));
    updateDay(d.day, { graded: true, wrong, quizDone: true, score: qs.length - wrong.length, gradedAt: ymd(new Date()) });
    renderQuiz(d.day);
    window.scrollTo(0, 0);
  });

  const retry = document.getElementById("retry");
  if (retry) retry.addEventListener("click", () => {
    const r = dayRecord(d.day);
    const again = shown.filter((i) => !right(i));
    const a = { ...(r.answers || {}) };
    again.forEach((i) => delete a[i]);
    updateDay(d.day, { graded: false, only: again, answers: a });
    renderQuiz(d.day);
    window.scrollTo(0, 0);
  });

  const fresh = document.getElementById("fresh");
  if (fresh) fresh.addEventListener("click", async () => {
    const msg = document.getElementById("qmsg");
    fresh.disabled = true;
    msg.innerHTML = `<span class="dot busy"></span>새 퀴즈를 만드는 중이에요`;
    try {
      const res = await postJSON("/api/quiz", { pages: store.pages.slice(d.start - 1, d.end), first: d.start, sections: (rec.note && rec.note.map) || [] });
      const old = dayRecord(d.day);
      updateDay(d.day, { quiz: res.quiz, quizSeconds: res.elapsed, answers: {}, graded: false, only: null, overrides: {}, flags: {},
        pastQuizzes: [...arr(old.pastQuizzes), { quiz: old.quiz, answers: old.answers, wrong: old.wrong }] });
      renderQuiz(d.day);
      window.scrollTo(0, 0);
    } catch (e) {
      msg.innerHTML = `<span class="dot bad"></span>${esc(e.message)}`;
      fresh.disabled = false;
    }
  });

  app.querySelectorAll("[data-override]").forEach((b) => b.addEventListener("click", () => {
    const r = dayRecord(d.day);
    const ov = { ...(r.overrides || {}), [b.dataset.override]: true };
    const wrong = arr(r.wrong).filter((i) => String(i) !== b.dataset.override);
    updateDay(d.day, { overrides: ov, wrong, score: qs.length - wrong.length });
    renderQuiz(d.day);
  }));

  app.querySelectorAll("[data-flag]").forEach((b) => b.addEventListener("click", () => {
    const r = dayRecord(d.day);
    const f = { ...(r.flags || {}) };
    f[b.dataset.flag] = f[b.dataset.flag] === b.dataset.kind ? undefined : b.dataset.kind;
    updateDay(d.day, { flags: f });
    const y = window.scrollY;
    renderQuiz(d.day);
    window.scrollTo(0, y);
  }));
}

// ---------- ⑤ 망각곡선 복습 (#5) ----------
// 퀴즈를 푼 날로부터 1일, 3일, 7일 뒤에 그날 문제를 다시 푼다.
// 복습 퀴즈는 AI를 다시 부르지 않고, 저장해 둔 문제 중 틀린 문제 위주로 골라 만든다.
const REVIEW_GAPS = [1, 3, 7];
const REVIEW_PER_DAY = 6;   // 한 Day에서 가져올 최대 문제 수
const REVIEW_MAX = 15;      // 한 번에 푸는 최대 문제 수

// 그 Day의 다음 복습 단계와 날짜. 다 끝났거나 시험 뒤면 null
function nextReview(day) {
  const r = dayRecord(day);
  if (!r.quizDone || !r.gradedAt || !r.quiz) return null;
  const done = r.reviews || {};
  for (let k = 0; k < REVIEW_GAPS.length; k++) {
    if (done[k]) continue;
    // 간격은 직전 복습을 한 날부터 센다. 복습이 밀려도 다음 복습이 한꺼번에 몰리지 않게
    const base = k === 0 ? r.gradedAt : (done[k - 1] && done[k - 1].date) || r.gradedAt;
    const due = addDays(base, REVIEW_GAPS[k] - (k ? REVIEW_GAPS[k - 1] : 0));
    if (store.examDate && due > store.examDate) return null;  // 시험 뒤 복습은 안 잡는다
    return { day: +day, stage: k, gap: REVIEW_GAPS[k], due };
  }
  return null;
}

function reviewsDue(today) {
  return Object.keys(store.days || {}).map(nextReview).filter((x) => x && x.due <= today)
    .sort((a, b) => a.due.localeCompare(b.due) || a.day - b.day);
}

function upcomingReview(today) {
  return Object.keys(store.days || {}).map(nextReview).filter((x) => x && x.due > today)
    .sort((a, b) => a.due.localeCompare(b.due))[0];
}

function planOf(day) { return store.plan.find((p) => p.day === +day); }

// Day마다 1·3·7일 차 복습이 언제인지. 끝난 건 그 날짜, 아직이면 예정일(앞 복습을 제때 한다고 보고 계산)
function reviewSchedule(day) {
  const r = dayRecord(day);
  if (!r.quizDone || !r.gradedAt) return null;
  const done = r.reviews || {};
  let base = r.gradedAt;
  return REVIEW_GAPS.map((gap, k) => {
    if (done[k]) { base = done[k].date; return { gap, state: "done", date: done[k].date, score: done[k] }; }
    const due = addDays(base, gap - (k ? REVIEW_GAPS[k - 1] : 0));
    base = due;
    if (store.examDate && due > store.examDate) return { gap, state: "after", date: due };
    return { gap, state: "todo", date: due };
  });
}

function scheduleHTML(today) {
  const days = store.plan.filter((p) => reviewSchedule(p.day));
  if (!days.length) return `<section class="section"><h2 style="font-size:17px">복습 일정</h2>
    <p class="hint" style="margin:0">아직 채점한 퀴즈가 없어요. 오늘 퀴즈를 풀면 여기에 일정이 생겨요.</p></section>`;
  const cell = (c) => {
    if (c.state === "done") return `<span class="sched done">✓ ${md(c.date)}<small>${c.score.score}/${c.score.total}</small></span>`;
    if (c.state === "after") return `<span class="sched after">시험 뒤</span>`;
    const cls = c.date < today ? "late" : c.date === today ? "now" : "";
    return `<span class="sched ${cls}">${c.date === today ? "오늘" : md(c.date)}</span>`;
  };
  return `<section class="section">
    <div style="display:flex;justify-content:space-between;align-items:baseline"><h2 style="font-size:17px">복습 일정</h2><span class="hint">시험 ${korDate(store.examDate)}</span></div>
    <table class="sched-table">
      <thead><tr><th scope="col">공부한 날</th>${REVIEW_GAPS.map((g) => `<th scope="col">${g}일 차</th>`).join("")}</tr></thead>
      <tbody>${days.map((p) => `<tr><th scope="row"><b>Day ${p.day}</b><span>${esc(p.label)}</span></th>${reviewSchedule(p.day).map((c) => `<td>${cell(c)}</td>`).join("")}</tr>`).join("")}</tbody>
    </table>
  </section>`;
}

function reviewSectionHTML(today) {
  const due = reviewsDue(today);
  if (!due.length) {
    const next = upcomingReview(today);
    if (!next) return "";
    return `<section class="section ruled"><h2 class="label">복습</h2>
      <p class="hint" style="margin:6px 0 0">다음 복습은 ${korDate(next.due)} · Day ${next.day} ${next.gap}일 차예요</p></section>`;
  }
  const rows = due.map((r) => {
    const rec = dayRecord(r.day);
    const wrong = (rec.reviewWrong || rec.wrong || []).length;
    const late = r.due < today ? ` · <span style="color:var(--bad)">${diffDays(r.due, today)}일 밀림</span>` : "";
    return `<li><span class="grow">Day ${r.day} · ${esc(planOf(r.day).label)}</span>
      <span class="hint">${r.gap}일 차${wrong ? ` · 틀린 문제 ${wrong}개` : ""}${late}</span></li>`;
  }).join("");
  return `<section class="section ruled">
    <h2 class="label">오늘 복습</h2>
    <ul class="rows" style="border-top:0">${rows}</ul>
    <div class="actions" style="margin-top:12px"><a href="#/review" class="review-go">복습 퀴즈 풀기 →</a>
    <span class="hint">잊어버릴 때쯤 다시 풀면 오래 기억해요</span></div>
  </section>`;
}

// 복습 문제 고르기: 틀린 문제 전부 + 맞힌 문제 몇 개 (같은 날 여러 번 열어도 같은 문제)
function pickReviewQuestions(due) {
  const items = [];
  for (const r of due) {
    const rec = dayRecord(r.day);
    const qs = arr(rec.quiz && rec.quiz.questions);
    const wrong = (rec.reviewWrong || rec.wrong || []).filter((i) => qs[i]);
    const others = qs.map((q, i) => i).filter((i) => !wrong.includes(i));
    shuffleInPlace(others);
    const take = [...wrong, ...others].slice(0, REVIEW_PER_DAY);
    for (const qi of take) items.push({ day: r.day, stage: r.stage, qi, q: shuffledCopy(qs[qi]) });
  }
  return items.slice(0, REVIEW_MAX);
}

function shuffleInPlace(a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

// 보기 순서를 다시 섞은 복사본 (처음 풀 때 위치를 외워서 맞히지 않게)
function shuffledCopy(q) {
  const c = JSON.parse(JSON.stringify(q));
  if (c.type !== "choice" || !Array.isArray(c.options)) return c;
  const order = shuffleInPlace(c.options.map((_, i) => i));
  const ai = +c.answer_index;
  c.options = order.map((i) => q.options[i]);
  c.answer_index = order.indexOf(ai - 1) + 1;
  return c;
}

function loadSession(today) {
  let sess = store.reviewSession;
  if (sess && sess.date === today) return sess;
  const due = reviewsDue(today);
  if (!due.length) return null;
  sess = { date: today, items: pickReviewQuestions(due), answers: {}, graded: false };
  store = load(); store.reviewSession = sess; save(store);
  return sess;
}

function saveSession(key, patch) {
  store = load();
  store[key] = { ...store[key], ...patch };
  save(store);
  return store[key];
}

// 정리본에서 섹션 하나 찾기 (퀴즈 문제의 section 이름으로)
function findSection(day, title) {
  const secs = arr(dayRecord(day).note && dayRecord(day).note.sections);
  const k = secs.findIndex((x) => x.title === title);
  return k >= 0 ? { k, sec: secs[k] } : null;
}

// 채점 후 "다시 볼 개념": 틀린 문제의 섹션에서 핵심(★★ 이상)과 함정만 짧게
function revisitHTML(wrongItems) {
  // 같은 단원에서 많이 틀린 순서로, 최대 6개
  const groups = new Map();
  for (const it of wrongItems) {
    const key = `${it.day}|${it.q.section}`;
    const g = groups.get(key) || { day: it.day, section: it.q.section, n: 0 };
    g.n += 1; groups.set(key, g);
  }
  const sorted = [...groups.values()].sort((a, b) => b.n - a.n || a.day - b.day);
  const cards = [];
  for (const g of sorted) {
    if (cards.length >= 6) break;
    const f = findSection(g.day, g.section);
    if (!f) continue;
    const pts = arr(f.sec.key_points).filter((x) => +x.importance >= 2).slice(0, 3);
    const traps = arr(f.sec.traps).slice(0, 2);
    cards.push(`<li class="revisit-card">
      <div class="revisit-head"><b>${esc(f.sec.title)}</b><span class="hint">Day ${g.day} · ${g.n}문제 틀림</span></div>
      ${pts.length ? `<ul>${pts.map((x) => `<li>${esc(x.text)}</li>`).join("")}</ul>` : f.sec.definition ? `<p>${esc(f.sec.definition)}</p>` : ""}
      ${traps.map((t) => `<p class="trap">주의: ${esc(t.text)}</p>`).join("")}
      <a href="#/note/${g.day}/s${f.k}">정리본에서 보기 →</a>
    </li>`);
  }
  if (!cards.length) return "";
  const more = sorted.length - cards.length;
  return `<section class="revisit"><h2>다시 볼 개념</h2><p class="hint" style="margin:0 0 12px">틀린 문제가 많이 나온 단원부터 핵심과 함정만 모았어요${more > 0 ? ` · 그 밖에 ${more}개 단원` : ""}</p><ul class="revisit-list">${cards.join("")}</ul></section>`;
}

// 복습 퀴즈와 총정리 퀴즈가 같이 쓰는 화면
function renderSessionQuiz(mode) {
  const today = ymd(new Date());
  const key = mode.key;
  const sess = store[key];
  const { items, graded } = sess;
  const answers = sess.answers || {};
  const right = (n) => isCorrect(items[n].q, answers[n]);
  const days = [...new Set(items.map((it) => it.day))];
  const score = items.filter((_, n) => right(n)).length;

  const qHTML = (it, n) => {
    const q = it.q;
    const d = planOf(it.day);
    const multi = new Set(store.pages.slice(d.start - 1, d.end).map((p) => p.file)).size > 1;
    const where = [`Day ${it.day}`, q.section, pageRange(q.pages, multi)].filter(Boolean).map(esc).join(" · ");
    const opts = q.type === "short"
      ? (graded
        ? `<p class="short-result">내 답 <b class="${right(n) ? "ok" : "bad"}">${esc(answers[n] || "(안 씀)")}</b> · 정답 <b>${esc(q.answer_text)}</b></p>`
        : `<input class="short" data-n="${n}" value="${esc(answers[n] || "")}" placeholder="답을 적어 주세요" aria-label="Q${n + 1} 답">`)
      : `<ol class="opts" role="radiogroup" aria-label="Q${n + 1} 보기">${arr(q.options).map((o, k) => {
        const v = k + 1, mine = +answers[n] === v, correct = +q.answer_index === v;
        if (!graded) return `<li><label class="opt ${mine ? "picked" : ""}"><input type="radio" name="r${n}" value="${v}" ${mine ? "checked" : ""} data-n="${n}"><span class="n">${v}</span><span>${esc(o)}</span></label></li>`;
        const cls = correct ? "ok" : mine ? "bad" : "";
        return `<li class="opt done ${cls}"><span class="n">${v}</span><span class="grow">${esc(o)}</span>${correct ? '<span class="tag">정답</span>' : mine ? '<span class="tag">내 답</span>' : ""}</li>`;
      }).join("")}</ol>`;
    const f = findSection(it.day, q.section);
    return `<article class="q ${graded ? (right(n) ? "is-ok" : "is-bad") : ""}">
      <span class="meta">Q${n + 1} · ${where}${graded ? ` · <b class="${right(n) ? "ok" : "bad"}">${right(n) ? "맞음" : "틀림"}</b>` : ""}</span>
      <h2>${esc(q.question)}</h2>
      ${q.code ? `<pre class="code">${esc(q.code)}</pre>` : ""}
      ${opts}
      ${graded ? `<div class="explain-box">${q.explanation ? `<span class="explain-label">해설</span><p class="explain">${esc(q.explanation)}</p>` : ""}
        <div class="explain-foot"><a class="see-note" href="#/note/${it.day}${f ? `/s${f.k}` : ""}">정리본에서 다시 보기 →</a></div></div>` : ""}
    </article>`;
  };

  const groups = days.map((d) => {
    const mine = items.filter((it) => it.day === d);
    return { day: d, n: mine.length, label: planOf(d).label, sub: mode.groupSub(mine[0]) };
  });
  const wrongItems = graded ? items.filter((_, n) => !right(n)) : [];
  app.innerHTML = `${navHeader("", true)}
  <main class="wide">
    <div class="review-grid">
      <aside class="review-side">
        <span class="step">${mode.step}</span>
        ${graded
          ? `<h1 class="title">${items.length}문제 중<br>${score}개 맞았어요</h1>
             <span class="hint">${mode.afterHint(score, items.length)}</span>`
          : `<h1 class="title">${mode.title}</h1>
             <span class="hint" id="left"></span>
             <div class="progress" role="progressbar" aria-label="푼 문제" aria-valuemin="0" aria-valuemax="${items.length}" id="bar"><div style="width:0%"></div></div>`}
        <ul class="review-days">${groups.map((g) => `<li><b>Day ${g.day}${g.sub ? ` · ${g.sub}` : ""}</b><span>${esc(g.label)} · ${g.n}문제</span></li>`).join("")}</ul>
        <div class="actions">
          ${graded ? `<a class="primary wide" href="#/today">오늘로 돌아가기</a>` : `<button class="primary wide" id="grade">채점하기</button>`}
        </div>
        <span id="qmsg" class="status" aria-live="polite"></span>
        ${graded ? "" : `<p class="hint" style="margin:0">${mode.note}</p>`}
      </aside>
      <div class="review-qs">${graded ? revisitHTML(wrongItems) : ""}${items.map(qHTML).join("")}</div>
    </div>
  </main>`;

  const countLeft = () => {
    const el = document.getElementById("left");
    if (!el) return;
    const a = (store[key] || {}).answers || {};
    const left = items.filter((_, n) => a[n] === undefined || a[n] === "").length;
    el.textContent = left ? `${items.length}문제 중 ${items.length - left}문제 풀었어요` : "다 풀었어요. 채점해 볼까요?";
    const bar = document.querySelector("#bar div");
    if (bar) bar.style.width = `${((items.length - left) / items.length) * 100}%`;
  };
  countLeft();
  const setAnswer = (n, v) => { saveSession(key, { answers: { ...(store[key].answers || {}), [n]: v } }); countLeft(); };
  app.querySelectorAll('input[type="radio"][data-n]').forEach((r) => r.addEventListener("change", () => {
    r.closest(".opts").querySelectorAll(".opt").forEach((l) => l.classList.remove("picked"));
    r.closest(".opt").classList.add("picked");
    setAnswer(r.dataset.n, +r.value);
  }));
  app.querySelectorAll("input.short").forEach((t) => t.addEventListener("input", () => setAnswer(t.dataset.n, t.value.trim())));

  const grade = document.getElementById("grade");
  if (grade) grade.addEventListener("click", () => {
    const a = store[key].answers || {};
    const left = items.filter((_, n) => a[n] === undefined || a[n] === "").length;
    if (left && grade.dataset.sure !== "1") {
      document.getElementById("qmsg").textContent = `아직 ${left}문제를 안 풀었어요. 그대로 채점하려면 한 번 더 눌러 주세요.`;
      grade.dataset.sure = "1";
      return;
    }
    for (const day of days) {
      const mine = items.map((it, n) => ({ it, n })).filter((x) => x.it.day === day);
      const wrongNow = mine.filter((x) => !isCorrect(x.it.q, a[x.n])).map((x) => x.it.qi);
      mode.onGradeDay(day, mine, wrongNow, today);
    }
    saveSession(key, { graded: true });
    mode.rerender();
    window.scrollTo(0, 0);
  });
}

const REVIEW_MODE = {
  key: "reviewSession",
  step: "복습 퀴즈",
  title: "잊기 전에<br>다시 풀어 봐요",
  note: "틀렸던 문제가 섞여 있어요. 보기 순서는 처음과 달라요.",
  groupSub: (it) => `${REVIEW_GAPS[it.stage]}일 차`,
  afterHint: (score, total) => (score === total ? "다 기억하고 있어요! 다음 복습 간격이 길어져요" : `틀린 ${total - score}문제는 다음 복습에 다시 나와요`),
  // Day마다 복습 결과를 남기고, 이번에 틀린 문제를 다음 복습의 "틀린 문제"로 쓴다
  onGradeDay: (day, mine, wrongNow, today) => {
    const rec = dayRecord(day);
    const stage = mine[0].it.stage;
    updateDay(day, {
      reviews: { ...(rec.reviews || {}), [stage]: { date: today, score: mine.length - wrongNow.length, total: mine.length } },
      reviewWrong: wrongNow,
    });
  },
  rerender: () => renderReview(),
};

function renderReview() {
  if (!store.plan) return redirect("#/upload");
  const today = ymd(new Date());
  const sess = loadSession(today);
  if (!sess || !sess.items.length) {
    const next = upcomingReview(today);
    app.innerHTML = `${navHeader("", true)}
    <main class="wide two-col">
      <div class="intro">
        <span class="step">복습</span>
        <h1 class="title hero">오늘은 복습할 게 없어요</h1>
        <p class="lede">${next ? `다음 복습은 <b>${korDate(next.due)}</b> · Day ${next.day} ${next.gap}일 차예요.` : "퀴즈를 채점하면 1일, 3일, 7일 뒤에 복습이 잡혀요."}</p>
        <p class="hint">잊어버릴 때쯤 다시 풀수록 오래 기억해요. 복습 퀴즈는 틀렸던 문제 위주로 나와요.</p>
        <div class="actions" style="margin-top:12px"><a class="primary" href="#/today">오늘로</a></div>
      </div>
      <div class="panel">${scheduleHTML(today)}</div>
    </main>`;
    return;
  }
  renderSessionQuiz(REVIEW_MODE);
}

// ---------- ⑦ 시험 전날 총정리 (#22) ----------
// 시험 전날은 새 범위 없이: 전체 요약본(정리본에서 코드로 모음) → 전체 범위 퀴즈(틀린 문제 위주)
const FINAL_MAX = 20;

// 총정리 날
// - 새 계획: 서버가 정해 준 날 (공부할 날이 하루뿐이면 null → 시험날에만 총정리 화면)
// - 예전 계획(총정리 날 없이 시험 전날까지 범위가 있던 계획): 시험 전날로 본다
function finalDay() {
  if (store.finalDate === null) return store.examDate;
  return store.finalDate || addDays(store.examDate, -1);
}

// 여러 번 틀리거나 "이해 안 돼요"를 누른 단원
function weakConcepts() {
  const m = new Map();
  for (const p of store.plan) {
    const r = dayRecord(p.day);
    const qs = arr(r.quiz && r.quiz.questions);
    const add = (qi, why) => {
      const q = qs[qi];
      if (!q || !q.section) return;
      const key = `${p.day}|${q.section}`;
      const e = m.get(key) || { day: p.day, section: q.section, count: 0, why: new Set() };
      e.count += 1; e.why.add(why); m.set(key, e);
    };
    arr(r.wrong).forEach((qi) => add(qi, "퀴즈"));
    arr(r.reviewWrong).forEach((qi) => add(qi, "복습"));
    arr(r.finalWrong).forEach((qi) => add(qi, "총정리"));
    Object.entries(r.flags || {}).forEach(([qi, k]) => k === "confused" && add(+qi, "이해 안 돼요"));
  }
  return [...m.values()].sort((a, b) => b.count - a.count);
}

function renderFinalToday(today) {
  const examDay = today >= store.examDate;
  const notDone = store.plan.filter((p) => !dayRecord(p.day).quizDone);
  const weak = weakConcepts().slice(0, 6);
  const fs = store.finalSession;
  const quizState = fs && fs.date === today && fs.graded
    ? `오늘 총정리 퀴즈 ${fs.items.length}문제 중 ${fs.items.filter((it, n) => isCorrect(it.q, (fs.answers || {})[n])).length}개 맞았어요`
    : "";
  app.innerHTML = `${navHeader("today", true)}
  <main class="wide two-col">
    <div class="intro">
      <span class="step">${korDate(today)} · ${examDay ? "<b style='color:var(--accent)'>시험날</b>" : "총정리 · <b style='color:var(--accent)'>D-1</b>"}</span>
      <h1 class="title hero">${examDay ? "오늘 시험이에요.<br>요약본만 한 번 훑어봐요" : "내일 시험이에요.<br>약한 것만 한 번 더 봐요"}</h1>
      <p class="lede">${examDay ? "새로 외우기보다 표시해 둔 핵심과 함정만 확인해요." : "새 범위는 없어요. 전체 요약본으로 훑고, 지금까지 틀린 문제 위주로 전체 범위 퀴즈를 풀어요."}</p>
      <div class="actions" style="margin-top:8px">
        <a class="primary" href="#/final/summary">총정리 요약본 보기</a>
        ${examDay ? "" : `<a href="#/final/quiz" style="font-size:16px;font-weight:500">전체 범위 퀴즈 풀기</a>`}
      </div>
      ${quizState ? `<p class="status"><span class="dot ok"></span>${quizState}</p>` : ""}
    </div>
    <div class="panel">
      <section class="section">
        <h2 style="font-size:17px">자주 막힌 개념</h2>
        ${weak.length
          ? `<ul class="rows">${weak.map((w) => {
              const f = findSection(w.day, w.section);
              return `<li><a class="grow" href="#/note/${w.day}${f ? `/s${f.k}` : ""}" style="color:var(--text)">${esc(w.section)}</a>
                <span class="hint">Day ${w.day} · ${[...w.why].join("·")} ${w.count}번</span></li>`;
            }).join("")}</ul>`
          : `<p class="hint" style="margin:0">아직 틀린 문제가 없어요. 잘하고 있어요!</p>`}
      </section>
      ${notDone.length ? `<section class="section ruled">
        <h2 class="label">아직 퀴즈를 안 푼 날</h2>
        <ul class="rows" style="border-top:0">${notDone.map((p) => `<li><span class="grow">Day ${p.day} · ${esc(p.label)}</span>
          <a href="#/note/${p.day}" style="font-size:14px">정리본</a><a href="#/quiz/${p.day}" style="font-size:14px">퀴즈</a></li>`).join("")}</ul>
      </section>` : ""}
    </div>
  </main>`;
}

// 전체 요약본: 모든 Day 정리본에서 ★★ 이상 핵심, 함정, 서술형 한 문장만 모은다 (AI 없이)
function renderFinalSummary() {
  if (!store.plan) return redirect("#/upload");
  const weakKeys = new Set(weakConcepts().map((w) => `${w.day}|${w.section}`));
  const days = store.plan.map((p) => ({ p, note: dayRecord(p.day).note }));
  const comps = days.flatMap(({ note }) => arr(note && note.review && note.review.comparisons));
  let total = 0;
  const dayHTML = ({ p, note }, i) => {
    if (!note) return `<section class="paper unit" id="d${p.day}"><span class="tape" style="background:${TAPES[i % 3]}">Day ${p.day}</span>
      <h2>${esc(p.label)}</h2><p class="lead">정리본을 아직 안 만들었어요. <a href="#/today">오늘 화면</a>에서 이 Day를 열면 만들어요.</p></section>`;
    const secs = arr(note.sections).filter((x) => +x.importance >= 2 || weakKeys.has(`${p.day}|${x.title}`));
    total += secs.length;
    return `<section class="paper unit" id="d${p.day}">
      <span class="tape" style="background:${TAPES[i % 3]}">Day ${p.day}</span>
      <h2>${esc(note.title || p.label)}</h2>
      <p class="lead">${esc(p.label)} · 중요한 단원 ${secs.length}개</p>
      ${secs.map((x) => {
        const f = findSection(p.day, x.title);
        const pts = arr(x.key_points).filter((k) => +k.importance >= 3);
        const show = pts.length ? pts : arr(x.key_points).filter((k) => +k.importance >= 2).slice(0, 2);
        const weakMark = weakKeys.has(`${p.day}|${x.title}`) ? `<span class="weak-tag">틀린 적 있음</span>` : "";
        return `<h3><a href="#/note/${p.day}${f ? `/s${f.k}` : ""}" style="text-decoration:none">${esc(x.title)}</a> <span class="stars">${stars(x.importance)}</span>${weakMark}</h3>
          ${show.length ? `<ul>${show.map((k) => `<li><span class="u">${esc(k.text)}</span></li>`).join("")}</ul>` : ""}
          ${arr(x.traps).map((t) => `<span class="red">↳ 주의! ${esc(t.text)}</span>`).join("")}
          ${x.definition ? `<p class="memo" style="margin-top:6px">서술형 · ${esc(x.definition)}</p>` : ""}`;
      }).join("")}
    </section>`;
  };
  const body = days.map(dayHTML).join("");
  app.innerHTML = `<div class="note-page"><div class="note-wrap">
    <div class="note-top">
      <span class="muted">총정리 요약본 · 시험 ${korDate(store.examDate)}</span>
      <span style="display:flex;gap:8px;align-items:center"><a href="#/today" style="padding:10px 6px">← 오늘로</a><a class="pill" href="#/final/quiz">전체 퀴즈 ✎</a></span>
    </div>
    <header class="paper note-head">
      <div class="sub">시험 전날 총정리</div>
      <h1><span>한 장으로 보는 시험 범위</span></h1>
      <p>Day ${store.plan.length}개 정리본에서 ★★ 이상 단원 ${total}개의 핵심과 함정만 모았어요. "틀린 적 있음"은 퀴즈나 복습에서 틀린 단원이에요.</p>
    </header>
    <nav class="note-chips" aria-label="Day 바로가기">
      ${store.plan.map((p) => `<a href="#d${p.day}" data-jump="d${p.day}">Day ${p.day}</a>`).join("")}
      ${comps.length ? `<a href="#cmp" data-jump="cmp">헷갈리는 쌍</a>` : ""}
    </nav>
    ${body}
    ${comps.length ? `<section class="paper unit" id="cmp"><span class="tape" style="background:#ffd3de">헷갈리는 쌍</span>
      ${comps.map((c) => `<h3>${esc(c.title)}</h3><div class="tbl"><table>
        <tr>${arr(c.header).map((h) => `<th>${esc(h)}</th>`).join("")}</tr>
        ${arr(c.rows).map((r) => `<tr>${arr(r).map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`).join("")}</table></div>`).join("")}</section>` : ""}
    <div class="note-end">
      <span class="hand" style="font-size:22px;color:#5d6880">다 훑었으면 전체 범위로 확인해 봐요!</span>
      <a class="big-quiz" href="#/final/quiz">전체 범위 퀴즈 풀기 →</a>
    </div>
  </div></div>`;
  app.querySelectorAll("[data-jump]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    document.getElementById(a.dataset.jump).scrollIntoView({ behavior: "smooth" });
  }));
}

// 전체 범위 퀴즈: Day마다 틀린 문제를 먼저, 남는 자리는 맞힌 문제로. 최대 20문제
function pickFinalQuestions() {
  const days = store.plan.filter((p) => arr(dayRecord(p.day).quiz && dayRecord(p.day).quiz.questions).length);
  if (!days.length) return [];
  const per = Math.max(3, Math.ceil(FINAL_MAX / days.length));
  const items = [];
  for (const p of days) {
    const r = dayRecord(p.day);
    const qs = arr(r.quiz.questions);
    const wrong = [...new Set([...arr(r.reviewWrong ?? r.wrong), ...arr(r.wrong)])].filter((i) => qs[i]);
    const others = shuffleInPlace(qs.map((_, i) => i).filter((i) => !wrong.includes(i)));
    for (const qi of [...wrong, ...others].slice(0, per)) items.push({ day: p.day, qi, q: shuffledCopy(qs[qi]) });
  }
  return items.slice(0, FINAL_MAX);
}

const FINAL_MODE = {
  key: "finalSession",
  step: "전체 범위 퀴즈",
  title: "내일 시험 전에<br>전체를 확인해요",
  note: "Day마다 틀렸던 문제가 먼저 나와요. 채점하면 틀린 단원을 '다시 볼 개념'으로 정리해 줘요.",
  groupSub: () => "",
  afterHint: (score, total) => (score === total ? "전 범위를 다 기억하고 있어요. 내일 잘 볼 거예요!" : `틀린 ${total - score}문제의 단원은 '다시 볼 개념'에서 한 번 더 봐요`),
  onGradeDay: (day, mine, wrongNow, today) => {
    updateDay(day, { finalWrong: wrongNow, finalScore: { date: today, score: mine.length - wrongNow.length, total: mine.length } });
  },
  rerender: () => renderFinalQuiz(),
};

function renderFinalQuiz() {
  if (!store.plan) return redirect("#/upload");
  const today = ymd(new Date());
  let sess = store.finalSession;
  if (!sess || sess.date !== today) {
    const items = pickFinalQuestions();
    if (!items.length) {
      app.innerHTML = `${navHeader("")}<main><div class="head"><h1 class="title">아직 푼 퀴즈가 없어요</h1>
        <span class="hint">Day별 퀴즈를 만들어야 전체 범위 퀴즈를 낼 수 있어요.</span></div>
        <div class="actions"><a class="primary" href="#/today">오늘로</a></div></main>`;
      return;
    }
    sess = { date: today, items, answers: {}, graded: false };
    store = load(); store.finalSession = sess; save(store);
  }
  renderSessionQuiz(FINAL_MODE);
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
  const [, page, arg, arg2] = location.hash.split("/");
  window.scrollTo(0, 0);
  if (page === "upload") return renderUpload();
  if (page === "plan") return renderPlan();
  if (page === "today") return renderToday();
  if (page === "note") return renderNote(arg, arg2);
  if (page === "quiz") return renderQuiz(arg);
  if (page === "review") return renderReview();
  if (page === "final") return arg === "quiz" ? renderFinalQuiz() : renderFinalSummary();
  if (page === "history") return renderSoon("지난 공부");
  if (page === "settings") return renderSoon("설정");
  redirect(store.plan ? "#/today" : "#/upload");
}
window.addEventListener("hashchange", route);
route();
