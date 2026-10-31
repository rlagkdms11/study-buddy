"""퀴즈 오답 보기 검사와 고치기 (#20)

AI가 만든 오답 보기가 강의 범위에 근거하는지 코드로 검사하고,
근거가 약한 보기만 AI에게 다시 만들게 한다.
"""
import re

# 조사·어미를 떼고 비교한다 (한국어는 "취약점을"처럼 붙어 나와서)
JOSA = ("으로써", "에서는", "에게서", "으로", "에서", "에게", "까지", "부터", "보다", "처럼", "하는", "하고", "하여", "되는", "된다",
        "한다", "이다", "이며", "하기", "해서", "을", "를", "이", "가", "은", "는", "의", "에", "와", "과", "로", "도", "만", "한", "된")
STOP = {"것", "수", "등", "때", "및", "위한", "대한", "통해", "모든", "가장", "있는", "없는", "있다", "없다", "같은", "다른", "특정", "경우"}
OUTSIDE = ("PDF 외", "pdf 외", "자료 외", "범위 외", "강의 외", "없는 내용")


def words(text: str) -> list[str]:
    """문장에서 내용 단어만 뽑는다 (2글자 이상, 조사 뗀 형태)."""
    out = []
    for w in re.findall(r"[가-힣A-Za-z0-9]+", text):
        for j in JOSA:
            if w.endswith(j) and len(w) - len(j) >= 2:
                w = w[: -len(j)]
                break
        if len(w) >= 2 and w not in STOP:
            out.append(w.lower())
    return out


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def grounding(option: str, source_compact: str) -> float:
    """보기의 내용 단어 중 강의 범위 글자에 실제로 나오는 비율 (0~1)."""
    ws = words(option)
    if not ws:
        return 1.0
    return sum(1 for w in ws if w in source_compact) / len(ws)


def find_weak(quiz: dict, source: str) -> list[dict]:
    """근거가 약한 오답 보기 목록. 정답 문장을 일부 바꾼 보기("나:")는 기준을 낮춘다."""
    src = compact(source)
    weak = []
    for qi, q in enumerate(quiz.get("questions", [])):
        if q.get("type") != "choice":
            continue
        sources = q.get("option_sources") or []
        for oi, opt in enumerate(q.get("options", [])):
            if oi + 1 == q.get("answer_index"):
                continue
            tag = sources[oi] if oi < len(sources) else ""
            g = grounding(opt, src)
            limit = 0.34 if str(tag).startswith("나") else 0.5
            if g < limit or any(o in str(tag) for o in OUTSIDE):
                weak.append({"q": qi, "o": oi, "option": opt, "grounding": round(g, 2), "source": tag})
    return weak


def fix_prompt(quiz: dict, weak: list[dict]) -> str:
    """근거 약한 보기만 다시 만들어 달라는 프롬프트."""
    concepts = ", ".join(c.get("term", "") for c in quiz.get("concepts", []) if c.get("term"))
    lines = []
    by_q = {}
    for w in weak:
        by_q.setdefault(w["q"], []).append(w["o"])
    for qi, bad in by_q.items():
        q = quiz["questions"][qi]
        opts = "\n".join(
            f'    {i + 1}. {o}' + ("  ← 정답" if i + 1 == q.get("answer_index") else "  ← 바꾸기" if i in bad else "")
            for i, o in enumerate(q.get("options", []))
        )
        lines.append(f'- 문제 {qi + 1}: {q.get("question")}\n{opts}')
    return f"""너는 대학생 시험 퀴즈를 검토하는 조교야.
아래 오답 보기들은 강의 범위에 없는 내용이라, 몰라도 소거법으로 풀려. 각각 새 오답 보기로 바꿔 줘.

규칙
- 새 보기는 반드시 이 범위 개념 중 하나로 만들거나, 정답 문장에서 한 부분(숫자, 주체, 조건, 범위)만 틀리게 바꿔.
- 이 범위 개념: {concepts}
- 같은 문제의 다른 보기와 겹치면 안 되고, 정답이 되어서도 안 돼.
- 길이와 말투는 같은 문제의 다른 보기와 비슷하게.
- 한국어로 쓰고 마크다운 기호는 쓰지 마.

바꿀 보기
{chr(10).join(lines)}

아래 JSON 형식으로만 답해. q와 o는 위에 적힌 문제 번호와 보기 번호 그대로.
{{"fixes": [{{"q": 1, "o": 3, "option": "새 보기", "source": "가: 개념 이름 또는 나: 바꾼 부분"}}]}}
"""


def apply_fixes(quiz: dict, fixes: list[dict]) -> int:
    """AI가 준 새 보기를 퀴즈에 넣는다. 넣은 개수를 돌려준다."""
    n = 0
    qs = quiz.get("questions", [])
    for f in fixes or []:
        try:
            qi, oi = int(f["q"]) - 1, int(f["o"]) - 1
            q = qs[qi]
            if q.get("type") != "choice" or oi + 1 == q.get("answer_index") or not 0 <= oi < len(q["options"]):
                continue
            new = str(f.get("option", "")).strip()
            if not new or new in q["options"]:
                continue
            q["options"][oi] = new
            if isinstance(q.get("option_sources"), list) and oi < len(q["option_sources"]):
                q["option_sources"][oi] = str(f.get("source", "고침"))
            n += 1
        except (KeyError, ValueError, TypeError, IndexError):
            continue
    return n


def check_and_fix(quiz: dict, source: str, ask) -> dict:
    """검사 → 근거 약한 보기만 한 번 다시 만들기 → 다시 검사. ask는 (prompt) -> dict."""
    before = find_weak(quiz, source)
    report = {"weak_before": len(before), "fixed": 0, "weak_after": len(before)}
    if before:
        try:
            res = ask(fix_prompt(quiz, before))
            report["fixed"] = apply_fixes(quiz, res.get("fixes", []))
        except Exception:
            pass  # 고치기에 실패해도 원래 퀴즈는 그대로 쓴다
        report["weak_after"] = len(find_weak(quiz, source))
    return report
