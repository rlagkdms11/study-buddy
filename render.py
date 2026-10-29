import streamlit as st


def stars(n):
    """중요도 숫자를 별로 바꾼다. 3 → ★★★"""
    return "★" * int(n or 0)


def render_note(note: dict, page_label=lambda p: f"p.{p}"):
    """AI가 준 정리본 JSON을 PPT 순서대로 화면에 그린다. page_label은 쪽 번호 표시 방법."""
    st.header(note.get("title", "정리본"))

    st.subheader("한 장으로 보는 전체 지도")
    st.write(" → ".join(note.get("map", [])))

    st.subheader("공부 순서")
    for i, item in enumerate(note.get("study_order", [])):
        st.checkbox(item, key=f"order_{i}")

    for n, sec in enumerate(note.get("sections", []), start=1):
        st.divider()
        pages = ", ".join(page_label(p) for p in sec.get("pages", []))
        st.subheader(f"{n}. {sec.get('title', '')}  {stars(sec.get('importance'))}")
        st.caption(f"{pages} · {sec.get('link', '')}")

        left, right = st.columns(2)
        left.info(f"**왜 필요했나**\n\n{sec.get('why', '')}")
        right.success(f"**그래서**\n\n{sec.get('so', '')}")
        if sec.get("analogy"):
            st.caption(f"비유 (PDF에 없는 설명): {sec['analogy']}")

        for kp in sec.get("key_points", []):
            st.markdown(f"- {kp.get('text', '')} {stars(kp.get('importance'))}")

        if sec.get("clues"):
            st.markdown("**이게 보이면 → 답**")
            st.table([{"이런 문장이 보이면": c.get("clue", ""), "답": c.get("answer", "")} for c in sec["clues"]])

        for t in sec.get("traps", []):
            st.warning(f"함정 {stars(t.get('importance'))}: {t.get('text', '')}")

        if sec.get("definition"):
            st.markdown(f"**서술형 한 문장:** {sec['definition']}")

        check = sec.get("check")
        if check:
            with st.expander(f"확인 질문: {check.get('q', '')}"):
                st.write(check.get("a", ""))

    comparisons = note.get("review", {}).get("comparisons", [])
    if comparisons:
        st.divider()
        st.subheader("마지막 정리: 헷갈리는 개념 비교")
        for comp in comparisons:
            st.markdown(f"**{comp.get('title', '')}**")
            header = comp.get("header", [])
            st.table([dict(zip(header, row)) for row in comp.get("rows", [])])


def render_quiz(quiz: dict, page_label=lambda p: f"p.{p}"):
    """퀴즈 JSON을 문제지로 그리고, 채점하기를 누르면 결과를 보여 준다."""
    questions = quiz.get("questions", [])

    with st.form("quiz_form"):
        for i, q in enumerate(questions, start=1):
            st.markdown(f"**Q{i}.** {q.get('question', '')}")
            if q.get("code"):
                st.code(q["code"], language=q.get("code_language", "java"))
            st.caption(f"{q.get('section', '')} {stars(q.get('importance'))}")

            if q.get("type") == "choice":
                options = q.get("options", [])
                st.radio(f"Q{i} 보기", list(range(1, len(options) + 1)), index=None,
                         format_func=lambda n, opts=options: f"{n}. {opts[n - 1]}",
                         key=f"q_{i}", label_visibility="collapsed")
            else:
                st.text_input(f"Q{i} 답", key=f"q_{i}",
                              label_visibility="collapsed", placeholder="답을 적어 보세요")
        submitted = st.form_submit_button("채점하기")

    if submitted:
        st.session_state["quiz_submitted"] = True
    if not st.session_state.get("quiz_submitted"):
        return

    st.divider()
    st.subheader("채점 결과")
    correct, total = 0, 0
    for i, q in enumerate(questions, start=1):
        mine = st.session_state.get(f"q_{i}")
        pages = ", ".join(page_label(p) for p in q.get("pages", []))

        if q.get("type") == "choice":
            total += 1
            options = q.get("options", [])
            answer = q.get("answer_index", 0)
            answer_text = options[answer - 1] if 1 <= answer <= len(options) else q.get("answer_text", "")
            mine_text = f"{mine}번" if mine else "선택 안 함"
            if mine == answer:
                correct += 1
                st.success(f"Q{i} 정답! {answer}번")
            else:
                st.error(f"Q{i} 오답. 내 답: {mine_text} / 정답: {answer}번")
            st.caption(f"정답 {answer}번: {answer_text}")
        else:
            st.info(f"Q{i} 단답형. 내 답: {mine or '(입력 안 함)'} / 정답: {q.get('answer_text', '')}")
        st.caption(f"해설: {q.get('explanation', '')} ({pages})")

    if total:
        st.metric("객관식 점수", f"{correct} / {total}")