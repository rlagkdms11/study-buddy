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


def concept_terms(quiz: dict) -> list[str]:
    return [str(c.get("term", "")).strip() for c in quiz.get("concepts", []) if str(c.get("term", "")).strip()]


def rewrite_prompt(quiz: dict, qis: list[int]) -> str:
    """보기를 고쳐도 엉뚱하면, 문제를 '설명 보고 개념 고르기'로 통째로 바꾸게 한다."""
    terms = concept_terms(quiz)
    lines = [f'- 문제 {qi + 1}: {quiz["questions"][qi].get("question")} (정답: {quiz["questions"][qi].get("answer_text")})' for qi in qis]
    return f"""너는 대학생 시험 퀴즈를 검토하는 조교야.
아래 문제들은 오답 보기가 강의에 없는 내용이라 소거법으로 풀려. 각 문제를 "설명을 보고 개념 고르기" 문제로 다시 만들어 줘.

규칙
- question: 이 문제가 묻던 내용을 강의 범위 근거로 설명하는 한두 문장 + "이 설명에 해당하는 것은?"
- options: 아래 개념 목록에서 정확히 같은 글자로 4개만 골라. 정답 1개 + 헷갈리기 쉬운 개념 3개.
- 개념 목록: {" | ".join(terms)}
- answer_index는 정답 보기 번호(1~4), answer_text는 정답 보기 글자 그대로.
- explanation은 정답인 이유와 가장 헷갈리는 오답이 틀린 이유를 한두 문장으로.
- 한국어로 쓰고 마크다운 기호는 쓰지 마.

다시 만들 문제
{chr(10).join(lines)}

아래 JSON 형식으로만 답해. q는 위에 적힌 문제 번호 그대로.
{{"rewrites": [{{"q": 1, "question": "설명... 이 설명에 해당하는 것은?", "options": ["개념", "개념", "개념", "개념"], "answer_index": 2, "answer_text": "개념", "explanation": "해설"}}]}}
"""


def apply_rewrites(quiz: dict, rewrites: list[dict], qis: list[int]) -> int:
    """보기 4개가 모두 개념 목록에 있을 때만 바꿔 끼운다. 코드로 확인하니 엉뚱한 보기가 들어올 수 없다."""
    terms = {compact(t): t for t in concept_terms(quiz)}
    n = 0
    for r in rewrites or []:
        try:
            qi = int(r["q"]) - 1
            opts = [str(o).strip() for o in r["options"]]
            ai = int(r["answer_index"])
        except (KeyError, ValueError, TypeError):
            continue
        if qi not in qis or len(opts) != 4 or len({compact(o) for o in opts}) != 4 or not 1 <= ai <= 4:
            continue
        if not all(compact(o) in terms for o in opts):
            continue
        q = quiz["questions"][qi]
        q.update({
            "question": str(r.get("question", q.get("question"))),
            "options": [terms[compact(o)] for o in opts],
            "option_sources": ["정답" if i + 1 == ai else f"가: {o}" for i, o in enumerate(opts)],
            "answer_index": ai,
            "answer_text": terms[compact(opts[ai - 1])],
            "explanation": str(r.get("explanation", q.get("explanation", ""))),
            "code": "",
        })
        n += 1
    return n


def check_and_fix(quiz: dict, source: str, ask) -> dict:
    """1단계: 근거 약한 보기만 다시 만들기
    2단계: 그래도 남으면 그 문제를 '개념 고르기' 문제로 바꾸기 (보기는 개념 목록에서만, 코드로 확인)
    3단계: 그래도 남으면 그 문제는 뺀다
    ask는 (prompt) -> dict. 단계가 실패해도 원래 퀴즈는 쓸 수 있게 둔다."""
    weak = find_weak(quiz, source)
    report = {"weak_before": len(weak), "fixed": 0, "rewritten": 0, "dropped": 0, "weak_after": len(weak)}
    if not weak:
        return report
    try:
        res = ask(fix_prompt(quiz, weak))
        report["fixed"] = apply_fixes(quiz, res.get("fixes", []))
    except Exception:
        pass
    left = sorted({w["q"] for w in find_weak(quiz, source)})
    if left and len(concept_terms(quiz)) >= 4:
        try:
            res = ask(rewrite_prompt(quiz, left))
            report["rewritten"] = apply_rewrites(quiz, res.get("rewrites", []), left)
        except Exception:
            pass
    left = sorted({w["q"] for w in find_weak(quiz, source)})
    if left:
        quiz["questions"] = [q for i, q in enumerate(quiz.get("questions", [])) if i not in left]
        report["dropped"] = len(left)
    report["weak_after"] = len(find_weak(quiz, source))
    return report


def find_structure_issues(quiz: dict, first: int, last: int) -> dict:
    """보기 내용 말고 퀴즈 모양의 실수를 센다 (비교 스크립트에서 사용).
    - 정답 불일치: answer_index가 가리키는 보기와 answer_text가 다름
    - 보기 중복: 같은 문제에 같은 보기가 두 번
    - 범위 밖 쪽: 근거 쪽 번호가 오늘 범위(first~last) 밖
    - 정답 위치: 객관식 정답 번호별 개수 (한쪽으로 쏠리면 찍어서 맞힘)
    """
    issues = {"정답 불일치": [], "보기 중복": [], "범위 밖 쪽": []}
    positions = [0, 0, 0, 0]
    for n, q in enumerate(quiz.get("questions", []), start=1):
        for p in q.get("pages") or []:
            if not isinstance(p, int) or not first <= p <= last:
                issues["범위 밖 쪽"].append(f"Q{n} p.{p}")
        if q.get("type") != "choice":
            continue
        opts = q.get("options") or []
        ai = q.get("answer_index")
        if not isinstance(ai, int) or not 1 <= ai <= len(opts):
            issues["정답 불일치"].append(f"Q{n} 정답 번호 {ai}")
            continue
        positions[min(ai, 4) - 1] += 1
        a, b = compact(str(q.get("answer_text", ""))), compact(opts[ai - 1])
        if a and a != b and a not in b and b not in a:
            issues["정답 불일치"].append(f"Q{n} {ai}번={opts[ai - 1][:20]} / 정답칸={q.get('answer_text')}")
        if len({compact(o) for o in opts}) != len(opts):
            issues["보기 중복"].append(f"Q{n}")
    return {"issues": issues, "positions": positions}


def shuffle_options(quiz: dict, rng=None) -> None:
    """객관식 보기 순서를 코드로 섞는다. AI는 정답을 2번에 몰아 두는 버릇이 있어서,
    정답 위치로 찍어 맞히지 못하게 한다. answer_index와 option_sources도 같이 옮긴다."""
    import random
    rng = rng or random.Random()
    for q in quiz.get("questions", []):
        opts = q.get("options") or []
        ai = q.get("answer_index")
        if q.get("type") != "choice" or not isinstance(ai, int) or not 1 <= ai <= len(opts):
            continue
        order = list(range(len(opts)))
        rng.shuffle(order)
        q["options"] = [opts[i] for i in order]
        src = q.get("option_sources")
        if isinstance(src, list) and len(src) == len(opts):
            q["option_sources"] = [src[i] for i in order]
        q["answer_index"] = order.index(ai - 1) + 1
