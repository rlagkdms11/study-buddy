import re
import time
from datetime import date, timedelta

import streamlit as st
import pymupdf

from ai import ask_ai
from prompts import SUMMARY_PROMPT, QUIZ_PROMPT
from render import render_note, render_quiz

# ▼ 브라우저 탭 이름과 아이콘 (Streamlit 명령 중 가장 먼저 와야 한다)
st.set_page_config(page_title="study-buddy", page_icon="📚")

# ▼ 처음 온 사람을 위한 소개와 사용 순서
st.title("📚 study-buddy")
st.write("강의 PDF를 올리면 시험일까지 공부 범위를 나눠 주고, 그날 범위로 정리본과 복습 퀴즈를 만들어 줘요.")
st.caption("① PDF 올리기 → ② 시험일 고르기 → ③ 정리본 만들기 → ④ 퀴즈 풀기")

# ▼ 개발용 화면은 사이드바 스위치를 켰을 때만 보인다
with st.sidebar:
    dev_mode = st.toggle("개발자 모드", help="추출한 텍스트와 AI 원본 응답을 보여 줘요")

pdfs = st.file_uploader("강의 PDF를 올려 주세요 (여러 개 가능)", type="pdf", accept_multiple_files=True)


def natural_key(name):
    """'2강'이 '10강'보다 앞에 오도록 이름 속 숫자를 숫자로 비교한다."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


@st.cache_data(show_spinner=False)
def extract_pages(data: bytes):
    """PDF를 페이지별 텍스트 목록으로 바꾼다. 같은 파일은 다시 읽지 않는다."""
    doc = pymupdf.open(stream=data, filetype="pdf")
    pages = []
    for page in doc:
        blocks = page.get_text("blocks", sort=True)
        texts = [b[4].replace("\n", " ").strip() for b in blocks if b[6] == 0]
        pages.append("\n".join(t for t in texts if t))
    doc.close()
    return pages


def load_all(files):
    """여러 PDF를 강의 순서대로 정렬해 페이지를 한 줄로 이어 붙인다."""
    files = sorted(files, key=lambda f: natural_key(f.name))
    items = []
    for f in files:
        title = f.name.removesuffix(".pdf")
        for i, text in enumerate(extract_pages(f.getvalue()), start=1):
            items.append({"file": title, "page": i, "text": text})
    return files, items


def build_pdf_text(items, first=1):
    """페이지마다 [전체 n쪽] 표시를 붙이고, 파일이 바뀔 때 강의 이름을 적는다."""
    lines, current = [], None
    for n, it in enumerate(items, start=first):
        if it["file"] != current:
            lines.append(f"===== 강의 자료: {it['file']} =====")
            current = it["file"]
        lines.append(f"[{n}쪽]\n{it['text']}")
    return "\n\n".join(lines)


def describe_range(items, start, end):
    """전체 start~end쪽을 '1강 8~10쪽, 2강 1~5쪽'처럼 파일별로 설명한다."""
    parts = []
    for it in items[start - 1:end]:
        if parts and parts[-1][0] == it["file"]:
            parts[-1][2] = it["page"]
        else:
            parts.append([it["file"], it["page"], it["page"]])
    return ", ".join(f"{f} {a}\\~{b}쪽" if a != b else f"{f} {a}쪽" for f, a, b in parts)


@st.cache_data(show_spinner=False)
def make_note(pdf_text: str):
    """같은 내용이면 AI를 다시 부르지 않고 저장된 결과를 돌려준다."""
    return ask_ai(SUMMARY_PROMPT + pdf_text, as_json=True)


@st.cache_data(show_spinner=False)
def make_quiz(pdf_text: str, sections: tuple):
    """퀴즈를 만든다. 정리본이 있으면 같은 섹션 이름을 쓰게 해서 둘을 연결한다."""
    hint = ""
    if sections:
        hint = "\nsection 칸에는 다음 섹션 제목 중 하나를 그대로 써: " + ", ".join(sections) + "\n"
    return ask_ai(QUIZ_PROMPT + hint + "\n강의 PDF 내용:\n" + pdf_text, as_json=True)


def make_plan(total_pages, start_date, exam_date):
    """공부 시작일부터 시험 전날까지 페이지를 하루씩 고르게 나눈다."""
    days = min((exam_date - start_date).days, total_pages)
    if days <= 0:
        return []
    base, extra = divmod(total_pages, days)
    plan, page = [], 1
    for d in range(days):
        count = base + (1 if d < extra else 0)
        plan.append({"day": d + 1, "date": start_date + timedelta(days=d),
                     "start": page, "end": page + count - 1})
        page += count
    return plan


def reset_results():
    """공부 범위가 바뀌면 이전 범위의 정리본·퀴즈·답을 지운다."""
    for key in ["note", "elapsed", "quiz", "quiz_elapsed", "quiz_submitted"]:
        st.session_state.pop(key, None)
    for key in [k for k in st.session_state if str(k).startswith(("q_", "order_"))]:
        del st.session_state[key]


if pdfs:
    files, items = load_all(pdfs)
    st.caption(f"자료 {len(files)}개 · 총 {len(items)}쪽 · 순서: " + " → ".join(f.name for f in files))

    def page_label(n):
        if not 1 <= n <= len(items):
            return f"p.{n}"
        it = items[n - 1]
        return f"p.{it['page']}" if len(files) == 1 else f"{it['file']} p.{it['page']}"

    if dev_mode:  # ▼ 개발자 모드에서만
        with st.expander("추출한 텍스트 보기"):
            for it in items:
                st.markdown(f"**{it['file']} {it['page']}쪽**")
                st.text(it["text"] or "(글자 없음)")

    st.subheader("📅 학습 계획")
    left, right = st.columns(2)
    start_date = left.date_input("공부 시작일", value=date.today())
    exam_date = right.date_input("시험일", value=date.today() + timedelta(days=7))

    plan = make_plan(len(items), start_date, exam_date)
    if not plan:
        st.warning("시험일은 공부 시작일보다 뒤로 골라 주세요.")
        st.stop()

    with st.expander(f"전체 계획 보기 ({len(plan)}일)"):  # ▼ 긴 표는 접어 둔다
        st.table([{"날짜": f"Day {p['day']} ({p['date']:%m/%d})",
                   "범위": describe_range(items, p["start"], p["end"])} for p in plan])

    today_idx = next((i for i, p in enumerate(plan) if p["date"] == date.today()), 0)
    idx = st.selectbox(
        "공부할 날", range(len(plan)), index=today_idx,
        format_func=lambda i: f"Day {plan[i]['day']} ({plan[i]['date']:%m/%d})",
    )
    chosen = plan[idx]
    count = chosen["end"] - chosen["start"] + 1
    st.success(f"오늘 범위: {describe_range(items, chosen['start'], chosen['end'])} ({count}쪽)")

    # ▼ 하루 분량이 많으면 미리 알려 준다
    if count > 20:
        st.warning(f"하루 {count}쪽이라 몇 분 걸릴 수 있어요. 시험일을 늦추면 하루 분량이 줄어요.")

    range_id = "|".join(f"{f.name}{f.size}" for f in files) + f"-{chosen['start']}-{chosen['end']}"
    if st.session_state.get("range_id") != range_id:
        reset_results()
        st.session_state["range_id"] = range_id

    today_items = items[chosen["start"] - 1:chosen["end"]]
    pdf_text = build_pdf_text(today_items, first=chosen["start"])

    # ▼ 정리본과 퀴즈를 탭으로 나눈다
    note_tab, quiz_tab = st.tabs(["📝 정리본", "✏️ 퀴즈"])

    with note_tab:
        if st.button("정리본 만들기"):
            try:
                start = time.perf_counter()
                with st.spinner(f"{count}쪽 정리본을 만드는 중... 보통 2~3분 걸려요. 창을 닫지 말아 주세요"):
                    st.session_state["note"] = make_note(pdf_text)
                st.session_state["elapsed"] = time.perf_counter() - start
            except Exception as e:
                st.error(f"정리본을 만들지 못했어요. 잠시 후 다시 시도해 주세요.\n\n({e})")

        if "note" in st.session_state:
            if "elapsed" in st.session_state:
                st.caption(f"정리본 생성: {st.session_state['elapsed']:.0f}초")
            render_note(st.session_state["note"], page_label=page_label)
            if dev_mode:
                with st.expander("AI가 보낸 원본 JSON 보기"):
                    st.json(st.session_state["note"])

    with quiz_tab:
        if "note" not in st.session_state:
            st.info("정리본을 먼저 만들면 퀴즈가 정리본 섹션과 연결돼요.")

        if st.button("퀴즈 만들기"):
            try:
                start = time.perf_counter()
                sections = tuple(st.session_state.get("note", {}).get("map", []))
                with st.spinner("퀴즈를 만드는 중... 보통 2~3분 걸려요. 창을 닫지 말아 주세요"):
                    quiz = make_quiz(pdf_text, sections)
                for key in [k for k in st.session_state if str(k).startswith("q_")]:
                    del st.session_state[key]
                st.session_state["quiz"] = quiz
                st.session_state["quiz_submitted"] = False
                st.session_state["quiz_elapsed"] = time.perf_counter() - start
            except Exception as e:
                st.error(f"퀴즈를 만들지 못했어요. 잠시 후 다시 시도해 주세요.\n\n({e})")

        if "quiz" in st.session_state:
            st.caption(f"퀴즈 생성: {st.session_state.get('quiz_elapsed', 0):.0f}초")
            render_quiz(st.session_state["quiz"], page_label=page_label)
            if dev_mode:
                with st.expander("AI가 보낸 퀴즈 원본 JSON 보기"):
                    st.json(st.session_state["quiz"])
else:
    st.info("PDF를 올리면 시작할 수 있어요.")