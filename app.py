import streamlit as st
import pymupdf

from ai import ask_ai

st.title("study-buddy")

pdf = st.file_uploader("강의 PDF를 올려 주세요", type="pdf")


def extract_pages(file):
    """PDF를 페이지별 텍스트 목록으로 바꾼다. 글 상자 단위로 위치 순서 정렬."""
    doc = pymupdf.open(stream=file.getvalue(), filetype="pdf")
    pages = []
    for page in doc:
        blocks = page.get_text("blocks", sort=True)
        # b[4] = 상자 안 글자, b[6] = 0이면 글자 상자 (1이면 이미지)
        texts = [b[4].replace("\n", " ").strip() for b in blocks if b[6] == 0]
        pages.append("\n".join(t for t in texts if t))
    doc.close()
    return pages


if pdf:
    pages = extract_pages(pdf)
    st.write(f"총 {len(pages)}쪽")

    for i, text in enumerate(pages, start=1):
        with st.expander(f"{i}쪽"):
            if text.strip():
                st.text(text)
            else:
                st.warning("글자를 찾지 못했어요. 이미지로 된 페이지일 수 있어요.")

    if st.button("AI 연결 테스트"):
        try:
            with st.spinner("AI에게 물어보는 중..."):
                answer = ask_ai("다음 강의 내용을 한 문장으로 요약해 줘:\n\n" + "\n".join(pages))
            st.success(answer)
        except Exception as e:
            st.error(f"AI 응답을 받지 못했어요. 잠시 후 다시 시도해 주세요.\n\n({e})")