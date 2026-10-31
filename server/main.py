"""study-buddy 웹 버전 백엔드.

서버는 아무것도 저장하지 않는다. PDF 글자, 계획, 정리본, 퀴즈, 내 답은
모두 브라우저(localStorage)에 저장하고, 필요할 때 그 내용을 다시 보내 준다.

실행: uvicorn server.main:app --reload
문서: http://127.0.0.1:8000/docs
"""
import logging
import time
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core import pdf
from core.ai import ask_ai
from core.plan import make_plan
from core.prompts import note_prompt, quiz_prompt

log = logging.getLogger("study-buddy")

MAX_PDF_MB = 30          # 파일 하나 최대 크기
MAX_PAGES_PER_CALL = 40  # 정리본·퀴즈 한 번에 보낼 수 있는 최대 쪽수

app = FastAPI(title="study-buddy API")


# ---------- 요청·응답 모양 ----------

class Page(BaseModel):
    file: str
    page: int
    text: str = ""


class PlanRequest(BaseModel):
    pages: list[Page] = Field(min_length=1)
    start_date: date
    exam_date: date


class NoteRequest(BaseModel):
    pages: list[Page] = Field(min_length=1, max_length=MAX_PAGES_PER_CALL)
    first: int = Field(1, ge=1, description="이 범위 첫 쪽의 전체 쪽 번호")


class QuizRequest(NoteRequest):
    sections: list[str] = []


# ---------- API ----------

@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/pdfs")
async def upload_pdfs(files: list[UploadFile] = File(...)):
    """PDF 여러 개를 받아 강의 순서대로 정렬하고 페이지별 글자를 돌려준다."""
    named = []
    for f in files:
        if not (f.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, f"PDF만 올릴 수 있어요: {f.filename}")
        data = await f.read()
        if len(data) > MAX_PDF_MB * 1024 * 1024:
            raise HTTPException(413, f"{f.filename}이(가) {MAX_PDF_MB}MB보다 커요.")
        named.append((f.filename, data))
    try:
        names, items = pdf.load_all(named)
    except Exception:
        log.exception("PDF 읽기 실패")
        raise HTTPException(400, "PDF를 읽지 못했어요. 파일이 깨졌거나 암호가 걸려 있는지 확인해 주세요.")

    counts = {}
    for it in items:
        counts[it["file"]] = counts.get(it["file"], 0) + 1
    return {
        "files": [{"name": n.removesuffix(".pdf"), "pages": counts.get(n.removesuffix(".pdf"), 0)} for n in names],
        "total_pages": len(items),
        "empty_pages": [i + 1 for i, it in enumerate(items) if not it["text"]],
        "pages": items,
    }


@app.post("/api/plan")
def plan(req: PlanRequest):
    """시험일까지 하루 분량을 나누고, 각 날 범위를 '1강 8~10쪽'처럼 설명한다."""
    items = [p.model_dump() for p in req.pages]
    days = make_plan(len(items), req.start_date, req.exam_date)
    if not days:
        raise HTTPException(400, "시험일은 공부 시작일보다 뒤로 골라 주세요.")
    for d in days:
        d["count"] = d["end"] - d["start"] + 1
        d["label"] = pdf.describe_range(items, d["start"], d["end"])
    return {"days": days}


def run_ai(prompt: str, what: str):
    """AI를 부르고 걸린 시간을 잰다. 실패하면 화면에 보여 줄 말로 바꾼다."""
    start = time.perf_counter()
    try:
        result = ask_ai(prompt, as_json=True)
    except RuntimeError as e:  # API 키 없음
        raise HTTPException(500, str(e))
    except ValueError:  # AI가 JSON이 아닌 답을 보냄
        log.exception("%s JSON 해석 실패", what)
        raise HTTPException(502, f"AI가 보낸 {what} 결과를 읽지 못했어요. 다시 시도해 주세요.")
    except Exception:
        log.exception("%s 생성 실패", what)
        raise HTTPException(503, "AI 서버가 지금 붐벼요. 잠시 후 다시 시도해 주세요.")
    return result, round(time.perf_counter() - start, 1)


@app.post("/api/note")
def note(req: NoteRequest):
    """오늘 범위로 정리본을 만든다. AI 호출이 길어서 일반 함수로 둔다(FastAPI가 별도 스레드에서 실행)."""
    text = pdf.build_pdf_text([p.model_dump() for p in req.pages], first=req.first)
    result, elapsed = run_ai(note_prompt(text), "정리본")
    return {"note": result, "elapsed": elapsed}


@app.post("/api/quiz")
def quiz(req: QuizRequest):
    """오늘 범위로 퀴즈를 만든다. 정리본 섹션 이름을 주면 퀴즈와 정리본이 연결된다."""
    text = pdf.build_pdf_text([p.model_dump() for p in req.pages], first=req.first)
    result, elapsed = run_ai(quiz_prompt(text, req.sections), "퀴즈")
    return {"quiz": result, "elapsed": elapsed}


# ---------- 화면 ----------
# web/ 폴더가 생기면 같은 서버에서 화면도 보여 준다 (API 경로보다 뒤에 둬야 한다)
WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
