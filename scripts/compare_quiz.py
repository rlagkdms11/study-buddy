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
import time
from datetime import datetime
from pathlib import Path

from core import pdf
from core.ai import ask_ai
from core.prompts import QUIZ_PROMPT
from core.quiz_check import check_and_fix, find_weak

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

def score_quiz(quiz: dict, source: str):
    """오답 보기 수와 근거 약한 보기 목록."""
    total = sum(len(q.get("options", [])) - 1 for q in quiz.get("questions", []) if q.get("type") == "choice")
    weak = [(w["q"] + 1, w["o"] + 1, w["grounding"], w["option"]) for w in find_weak(quiz, source)]
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
            if version == "새 프롬프트" and weak:
                print("  ▶ 자동 검사 + 고치기...", flush=True)
                t2 = time.perf_counter()
                check = check_and_fix(quiz, source, lambda pr: ask_ai(pr, as_json=True, models=[model]))
                sec2 = time.perf_counter() - t2
                total2, weak2 = score_quiz(quiz, source)
                fixed_name = name.replace(".json", "-fixed.json")
                (out_dir / fixed_name).write_text(json.dumps(quiz, ensure_ascii=False, indent=2), encoding="utf-8")
                rows.append(("새+자동검사", model, sec + sec2, total2, len(weak2), fixed_name))
                print(f"  {sec2:.0f}초 더 · 보기 고침 {check['fixed']} · 문제 바꿈 {check['rewritten']} · 뺌 {check['dropped']} · 남은 문제 {len(quiz['questions'])}개 · 남은 근거 약한 보기 {len(weak2)}개")
                for n, k, g, opt in weak2:
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
