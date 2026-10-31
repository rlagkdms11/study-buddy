"""퀴즈 보기 품질 비교 (#20)

같은 범위로 [이전 프롬프트 / 새 프롬프트] × [모델들]의 퀴즈를 만들고,
오답 보기가 강의 내용에 근거하는지 숫자로 비교한다.

실행 (프로젝트 폴더에서):
    python -m scripts.compare_quiz scripts/out/1강.pdf --start 1 --end 9
    python -m scripts.compare_quiz scripts/out/1강.pdf --ranges 1-5 6-10 1-9 --runs 3
    python -m scripts.compare_quiz 1강.pdf 2-3강.pdf --ranges 1-10 11-25 --models gemini-3.5-flash-lite gemini-3.8-flash

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
from core.quiz_check import check_and_fix, find_structure_issues, find_weak, shuffle_options

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


def run_once(prompt, text, source, model, first, last, fix):
    """퀴즈 하나를 만들고 (필요하면 자동 검사 후) 점수를 돌려준다."""
    start = time.perf_counter()
    quiz = ask_ai(prompt + "\n강의 PDF 내용:\n" + text, as_json=True, models=[model])
    check = None
    if fix:
        check = check_and_fix(quiz, source, lambda pr: ask_ai(pr, as_json=True, models=[model]))
        shuffle_options(quiz)
    sec = time.perf_counter() - start
    total, weak = score_quiz(quiz, source)
    shape = find_structure_issues(quiz, first, last)
    return quiz, {"sec": sec, "total": total, "weak": weak, "check": check, "shape": shape,
                  "questions": len(quiz.get("questions", []))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs="+", help="강의 PDF 파일")
    ap.add_argument("--ranges", nargs="+", default=None, help='비교할 범위들 (전체 쪽 번호). 예: 1-5 6-10')
    ap.add_argument("--start", type=int, default=1, help="--ranges 대신 범위 하나만 줄 때 시작")
    ap.add_argument("--end", type=int, default=10, help="--ranges 대신 범위 하나만 줄 때 끝")
    ap.add_argument("--runs", type=int, default=1, help="범위마다 몇 번씩 만들지")
    ap.add_argument("--models", nargs="+", default=["gemini-3.5-flash-lite"])
    args = ap.parse_args()

    files = [(Path(p).name, Path(p).read_bytes()) for p in args.pdfs]
    _, items = pdf.load_all(files)
    ranges = [tuple(map(int, r.split("-"))) for r in args.ranges] if args.ranges else [(args.start, args.end)]

    out_dir = Path(__file__).parent / "out"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%m%d-%H%M")
    versions = [("이전 프롬프트", OLD_QUIZ_PROMPT, False), ("새 프롬프트", QUIZ_PROMPT, False), ("새+자동검사", QUIZ_PROMPT, True)]
    results = {}  # (범위, 버전, 모델) -> [결과...]

    for a, b in ranges:
        chosen = items[a - 1: b]
        text = pdf.build_pdf_text(chosen, first=a)
        source = " ".join(it["text"] for it in chosen)
        print(f"■ 범위 {a}~{b}: {pdf.describe_range(items, a, b)} ({len(chosen)}쪽)")
        for run in range(1, args.runs + 1):
            for version, prompt, fix in versions:
                for model in args.models:
                    label = f"  {run}회 · {version} · {model}"
                    try:
                        quiz, r = run_once(prompt, text, source, model, a, b, fix)
                    except Exception as e:
                        print(f"{label}: 실패 ({str(e)[:60]})")
                        continue
                    results.setdefault((f"{a}-{b}", version, model), []).append(r)
                    tag = {"이전 프롬프트": "old", "새 프롬프트": "new", "새+자동검사": "fixed"}[version]
                    (out_dir / f"{stamp}-{a}-{b}-{run}-{tag}-{model}.json").write_text(json.dumps(quiz, ensure_ascii=False, indent=2), encoding="utf-8")
                    iss = r["shape"]["issues"]
                    extra = " · ".join(f"{k} {len(v)}" for k, v in iss.items() if v)
                    fixinfo = ""
                    if r["check"]:
                        c = r["check"]
                        fixinfo = f" (보기 고침 {c['fixed']} · 문제 바꿈 {c['rewritten']} · 뺌 {c['dropped']})"
                    print(f"{label}: {r['sec']:.0f}초 · 엉뚱한 오답 {len(r['weak'])}/{r['total']}{fixinfo}" + (f" · {extra}" if extra else ""))
                    for n, k, g, opt in r["weak"]:
                        print(f"      Q{n} 보기{k} ({g:.0%}): {opt}")
                    for k, v in iss.items():
                        for x in v:
                            print(f"      [{k}] {x}")
        print(flush=True)

    print("=" * 72)
    print("엉뚱한 오답 = 내용 단어의 절반 미만이 강의 범위에 나오는 오답 보기")
    print(f"{'범위':<8}{'버전':<12}{'엉뚱한 오답 (회차별)':<22}{'평균':>6}{'최악':>6}{'모양 실수':>10}{'시간':>7}")
    summary = {}
    for (rng, version, model), rs in results.items():
        ws = [len(r["weak"]) for r in rs]
        shape = sum(sum(len(v) for v in r["shape"]["issues"].values()) for r in rs)
        sec = sum(r["sec"] for r in rs) / len(rs)
        print(f"{rng:<8}{version:<12}{', '.join(map(str, ws)):<22}{sum(ws) / len(ws):>6.1f}{max(ws):>6}{shape:>10}{sec:>6.0f}초")
        s = summary.setdefault(version, {"weak": [], "shape": 0, "pos": [0, 0, 0, 0]})
        s["weak"] += ws
        s["shape"] += shape
        for r in rs:
            s["pos"] = [x + y for x, y in zip(s["pos"], r["shape"]["positions"])]
    print("-" * 72)
    for version, s in summary.items():
        n = len(s["weak"])
        zero = sum(1 for w in s["weak"] if w == 0)
        print(f"전체 {version}: 퀴즈 {n}개 · 엉뚱한 오답 평균 {sum(s['weak']) / n:.1f}개 · 0개인 퀴즈 {zero}/{n} · 모양 실수 {s['shape']} · 정답 위치 1~4번 {s['pos']}")
    print(f"\n퀴즈 원본: {out_dir}")


if __name__ == "__main__":
    main()
