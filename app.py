import time

import streamlit as st
import pymupdf

from ai import ask_ai
from prompts import SUMMARY_PROMPT, QUIZ_PROMPT
from render import render_note, render_quiz

st.title("study-buddy")

pdf = st.file_uploader("강의 PDF를 올려 주세요", type="pdf")


def extract_pages(file):
    """PDF를 페이지별 텍스트 목록으로 바꾼다. 글 상자 단위로 위치 순서 정렬."""
    doc = pymupdf.open(stream=file.getvalue(), filetype="pdf")
    pages = []
    for page in doc:
        blocks = page.get_text("blocks", sort=True)
        texts = [b[4].replace("\n", " ").strip() for b in blocks if b[6] == 0]
        pages.append("\n".join(t for t in texts if t))
    doc.close()
    return pages


def build_pdf_text(pages):
    """AI가 쪽 번호를 알 수 있게 페이지마다 [n쪽] 표시를 붙인다."""
    return "\n\n".join(f"[{i}쪽]\n{text}" for i, text in enumerate(pages, start=1))


@st.cache_data(show_spinner=False)
def make_note(pdf_text: str):
    """같은 PDF 내용이면 AI를 다시 부르지 않고 저장된 결과를 돌려준다."""
    return ask_ai(SUMMARY_PROMPT + pdf_text, as_json=True)


# ▼ 추가: 퀴즈 생성 함수
@st.cache_data(show_spinner=False)
def make_quiz(pdf_text: str, sections: tuple):
    """퀴즈를 만든다. 정리본이 있으면 같은 섹션 이름을 쓰게 해서 둘을 연결한다."""
    hint = ""
    if sections:
        hint = "\nsection 칸에는 다음 섹션 제목 중 하나를 그대로 써: " + ", ".join(sections) + "\n"
    return ask_ai(QUIZ_PROMPT + hint + "\n강의 PDF 내용:\n" + pdf_text, as_json=True)


if pdf:
    pages = extract_pages(pdf)

    with st.expander(f"추출한 텍스트 보기 (총 {len(pages)}쪽)"):
        for i, text in enumerate(pages, start=1):
            st.markdown(f"**{i}쪽**")
            st.text(text or "(글자 없음)")

    if st.button("정리본 만들기"):
        try:
            start = time.perf_counter()
            with st.spinner(f"{len(pages)}쪽 정리본을 만드는 중... 페이지가 많으면 몇 분 걸릴 수 있어요"):
                st.session_state["note"] = make_note(build_pdf_text(pages))
            st.session_state["elapsed"] = time.perf_counter() - start
        except Exception as e:
            st.error(f"정리본을 만들지 못했어요. 잠시 후 다시 시도해 주세요.\n\n({e})")

    if "note" in st.session_state:
        if "elapsed" in st.session_state:
            st.caption(f"정리본 생성: {st.session_state['elapsed']:.0f}초")
        render_note(st.session_state["note"])
        with st.expander("AI가 보낸 원본 JSON 보기"):
            st.json(st.session_state["note"])

    # ▼ 추가: 퀴즈 영역
    st.divider()
    st.header("복습 퀴즈")

    if st.button("퀴즈 만들기"):
        try:
            start = time.perf_counter()
            sections = tuple(st.session_state.get("note", {}).get("map", []))
            with st.spinner("퀴즈를 만드는 중..."):
                quiz = make_quiz(build_pdf_text(pages), sections)
            # 이전 퀴즈에서 고른 답을 지워서 새 퀴즈와 섞이지 않게 한다
            for key in [k for k in st.session_state if str(k).startswith("q_")]:
                del st.session_state[key]
            st.session_state["quiz"] = quiz
            st.session_state["quiz_submitted"] = False
            st.session_state["quiz_elapsed"] = time.perf_counter() - start
        except Exception as e:
            st.error(f"퀴즈를 만들지 못했어요. 잠시 후 다시 시도해 주세요.\n\n({e})")

    if "quiz" in st.session_state:
        st.caption(f"퀴즈 생성: {st.session_state.get('quiz_elapsed', 0):.0f}초")
        render_quiz(st.session_state["quiz"])
        with st.expander("AI가 보낸 퀴즈 원본 JSON 보기"):
            st.json(st.session_state["quiz"])