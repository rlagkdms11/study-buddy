"""PDF에서 글자를 뽑고, 쪽 범위를 설명하는 함수들. Streamlit과 FastAPI가 같이 쓴다."""
import re

import pymupdf


def natural_key(name: str):
    """'2강'이 '10강'보다 앞에 오도록 이름 속 숫자를 숫자로 비교한다."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def extract_pages(data: bytes) -> list[str]:
    """PDF를 페이지별 텍스트 목록으로 바꾼다. 글자 블록만 위→아래 순서로 읽는다."""
    doc = pymupdf.open(stream=data, filetype="pdf")
    pages = []
    for page in doc:
        blocks = page.get_text("blocks", sort=True)
        texts = [b[4].replace("\n", " ").strip() for b in blocks if b[6] == 0]
        pages.append("\n".join(t for t in texts if t))
    doc.close()
    return pages


def load_all(files: list[tuple[str, bytes]]):
    """(파일 이름, 내용) 목록을 강의 순서대로 정렬하고 페이지를 한 줄로 이어 붙인다.
    돌려주는 값: 정렬된 파일 이름 목록, [{"file", "page", "text"}, ...]
    """
    files = sorted(files, key=lambda f: natural_key(f[0]))
    items = []
    for name, data in files:
        title = name.removesuffix(".pdf")
        for i, text in enumerate(extract_pages(data), start=1):
            items.append({"file": title, "page": i, "text": text})
    return [name for name, _ in files], items


def build_pdf_text(items: list[dict], first: int = 1) -> str:
    """페이지마다 [전체 n쪽] 표시를 붙이고, 파일이 바뀔 때 강의 이름을 적는다."""
    lines, current = [], None
    for n, it in enumerate(items, start=first):
        if it["file"] != current:
            lines.append(f"===== 강의 자료: {it['file']} =====")
            current = it["file"]
        lines.append(f"[{n}쪽]\n{it['text']}")
    return "\n\n".join(lines)


def describe_range(items: list[dict], start: int, end: int) -> str:
    """전체 start~end쪽을 '1강 8~10쪽, 2강 1~5쪽'처럼 파일별로 설명한다."""
    parts = []
    for it in items[start - 1:end]:
        if parts and parts[-1][0] == it["file"]:
            parts[-1][2] = it["page"]
        else:
            parts.append([it["file"], it["page"], it["page"]])
    return ", ".join(f"{f} {a}~{b}쪽" if a != b else f"{f} {a}쪽" for f, a, b in parts)
