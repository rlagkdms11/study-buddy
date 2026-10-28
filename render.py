import streamlit as st


def stars(n):
    """중요도 숫자를 별로 바꾼다. 3 → ★★★"""
    return "★" * int(n or 0)


def render_note(note: dict):
    """AI가 준 정리본 JSON을 PPT 순서대로 화면에 그린다."""
    st.header(note.get("title", "정리본"))

    st.subheader("한 장으로 보는 전체 지도")
    st.write(" → ".join(note.get("map", [])))

    st.subheader("공부 순서")
    for i, item in enumerate(note.get("study_order", [])):
        st.checkbox(item, key=f"order_{i}")

    for n, sec in enumerate(note.get("sections", []), start=1):
        st.divider()
        pages = ", ".join(f"p.{p}" for p in sec.get("pages", []))
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