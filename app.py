import streamlit as st
import pymupdf

st.title("study-buddy")

pdf = st.file_uploader("강의 PDF를 올려 주세요", type="pdf")


def extract_pages(file):
    """PDF를 페이지별 텍스트 목록으로 바꾼다. 글 상자 단위로 위치 순서 정렬."""
    doc = pymupdf.open(stream=file.read(), filetype="pdf")
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