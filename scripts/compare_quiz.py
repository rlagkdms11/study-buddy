"""퀴즈 보기 품질 비교 (#20)

같은 범위로 [이전 프롬프트 / 새 프롬프트] × [모델들]의 퀴즈를 만들고,
오답 보기가 강의 내용에 근거하는지 숫자로 비교한다.

실행 (프로젝트 폴더에서):
    python -m scripts.compare_quiz "1강.pdf" --start 1 --end 9
    python -m scripts.compare_quiz "1강.pdf" "2-3강.pdf" --start 10 --end 20 --models gemini-3.5-flash-lite

결과: 화면에 요약, scripts/out/에 퀴즈 원본 JSON 저장
"""
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

from core import pdf
from core.ai import ask_ai
from core.prompts import QUIZ_PROMPT

OLD_QUIZ_PROMPT = """너는 대학생의 시험공부를 돕는 조교야.
아래 강의 PDF 내용으로 복습 퀴즈 10문항을 만들어 줘.

규칙
- 객관식 7문항, 단답형 3문항.
- 단순 암기만 묻지 말고, 개념을 이해했는지 확인하는 문제와 상황이나 코드를 보여 주고 어떤 개념인지 고르는 문제를 섞어.
- 객관식 보기는 4개이고, 정답 위치는 골고루 섞어.
- 오답 보기는 같은 강의에 나오는 다른 개념이나, 개념을 살짝 틀리게 바꾼 문장으로 만들어. 강의에 없는 엉뚱한 보기(법, 보안, 데이터베이스 등)는 쓰지 마. 몰라도 소거법으로 풀리는 문제는 피해.
- 용어는 PDF에 쓰인 표기 그대로 써. 예를 들어 PDF가 "싱글턴"이면 "싱글톤"으로 바꾸지 마.
- answer_index는 객관식 정답 보기의 번호(1~4). 단답형은 0.
- answer_text는 정답 내용. 객관식은 정답 보기 글자 그대로, 단답형은 짧은 정답.
- 모든 문제는 PDF 내용에 근거하고, pages에 근거 쪽 번호를 숫자로 적어. 쪽 번호는 내용 앞의 [n쪽] 표시를 따라.
- importance는 1~3 숫자야. 3이 시험 1순위.
- 모든 문장은 한국어로 쓰고, 마크다운 기호(**, # 등)는 쓰지 마.
- 문제에 코드가 필요하면 question에 넣지 말고 code 칸에 줄바꿈을 살려서 따로 써. 코드가 없으면 code는 빈 문자열 ""로 둬.

아래 JSON 형식으로만 답해. 단답형은 options를 빈 목록 []으로 둬.
{
  "questions": [
    {
      "section": "관련 섹션 제목",
      "type": "choice 또는 short",
      "question": "문제",
      "code": "",
      "code_language": "java",
      "options": ["보기1", "보기2", "보기3", "보기4"],
      "answer_index": 2,
      "answer_text": "정답",
      "explanation": "한 줄 해설",
      "pages": [4],
      "importance": 3
    }
  ]
}
"""

# 조사·어미를 떼고 비교한다 (한국어는 "취약점을"처럼 붙어 나와서)
JOSA = ("으로써", "에서는", "에게서", "으로", "에서", "에게", "까지", "부터", "보다", "처럼", "하는", "하고", "하여", "되는", "된다",
        "한다", "이다", "이며", "하기", "해서", "을", "를", "이", "가", "은", "는", "의", "에", "와", "과", "로", "도", "만", "한", "된")
STOP = {"것", "수", "등", "때", "및", "위한", "대한", "통해", "모든", "가장", "있는", "없는", "있다", "없다", "같은", "다른", "특정", "경우"}


def words(text: str) -> list[str]:
    """보기 문장에서 내용 단어만 뽑는다 (2글자 이상, 조사 뗀 형태)."""
    out = []
    for w in re.findall(r"[가-힣A-Za-z0-9]+", text):
        for j in JOSA:
            if w.endswith(j) and len(w) - len(j) >= 2:
                w = w[: -len(j)]
                break
        if len(w) >= 2 and w not in STOP:
            out.append(w.lower())
    return out


def grounding(option: str, source: str) -> float:
    """보기의 내용 단어 중 강의 범위 글자에 실제로 나오는 비율 (0~1)."""
    ws = words(option)
    if not ws:
        return 1.0
    return sum(1 for w in ws if w in source) / len(ws)


def score_quiz(quiz: dict, source: str, threshold: float = 0.5):
    """오답 보기마다 근거 비율을 재고, 기준보다 낮은 보기를 모은다."""
    src = re.sub(r"\s+", "", source).lower()
    total, weak = 0, []
    for n, q in enumerate(quiz.get("questions", []), start=1):
        if q.get("type") != "choice":
            continue
        for k, opt in enumerate(q.get("options", []), start=1):
            if k == q.get("answer_index"):
                continue
            total += 1
            g = grounding(opt, src)
            if g < threshold:
                weak.append((n, k, round(g, 2), opt))
    return total, weak


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+", help="강의 PDF 파일")
    ap.add_argument("--start", type=int, default=1, help="전체 쪽 번호 시작")
    ap.add_argument("--end", type=int, default=10, help="전체 쪽 번호 끝")
    ap.add_argument("--models", nargs="+", default=["gemini-3.5-flash-lite", "gemini-3.8-flash"])
    args = ap.parse_args()

    files = [(Path(p).name, Path(p).read_bytes()) for p in args.pdfs]
    _, items = pdf.load_all(files)
    chosen = items[args.start - 1: args.end]
    text = pdf.build_pdf_text(chosen, first=args.start)
    source = " ".join(it["text"] for it in chosen)
    print(f"범위: {pdf.describe_range(items, args.start, args.end)} ({len(chosen)}쪽)\n")

    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%m%d-%H%M")
    rows = []
    for version, prompt in [("이전 프롬프트", OLD_QUIZ_PROMPT), ("새 프롬프트", QUIZ_PROMPT)]:
        for model in args.models:
            print(f"▶ {version} · {model} 만드는 중...", flush=True)
            start = time.perf_counter()
            try:
                quiz = ask_ai(prompt + "\n강의 PDF 내용:\n" + text, as_json=True, models=[model])
            except Exception as e:
                print(f"  실패: {e}\n")
                rows.append((version, model, None, None, None, None))
                continue
            sec = time.perf_counter() - start
            total, weak = score_quiz(quiz, source)
            name = f"{stamp}-{'old' if version.startswith('이전') else 'new'}-{model}.json"
            (out_dir / name).write_text(json.dumps(quiz, ensure_ascii=False, indent=2), encoding="utf-8")
            rows.append((version, model, sec, total, len(weak), name))
            print(f"  {sec:.0f}초 · 오답 보기 {total}개 중 근거 약한 보기 {len(weak)}개")
            for n, k, g, opt in weak:
                print(f"    Q{n} 보기{k} (근거 {g:.0%}): {opt}")
            print()

    print("=" * 60)
    print(f"{'프롬프트':<10}{'모델':<26}{'시간':>6}{'근거 약한 오답':>14}")
    for version, model, sec, total, weak, _ in rows:
        if sec is None:
            print(f"{version:<10}{model:<26}{'실패':>6}")
        else:
            print(f"{version:<10}{model:<26}{sec:>5.0f}초{weak:>7} / {total}")
    print("\n근거 약한 오답 = 내용 단어의 절반 미만이 강의 범위에 나오는 보기 (엉뚱한 보기 후보)")
    print(f"퀴즈 원본: {out_dir}")


if __name__ == "__main__":
    main()
