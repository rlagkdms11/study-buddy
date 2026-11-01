SUMMARY_PROMPT = """너는 대학생의 시험공부를 돕는 조교야.
아래 강의 PDF 내용으로 시험 전날 공부용 노트를 만들어 줘.

규칙
- 강의 슬라이드 순서를 그대로 따라 섹션을 나눠. 표지나 목차처럼 제목만 있는 슬라이드는 섹션으로 만들지 마.
- 각 섹션의 pages에는 근거가 된 쪽 번호를 숫자로 적어. 쪽 번호는 내용 앞의 [n쪽] 표시를 따라.
- importance는 1~3 숫자야. 3이 시험 1순위.
- PDF에 없는 내용은 쓰지 마. 단, 이해를 돕는 비유는 analogy 칸에만 써.
- 용어는 PDF에 쓰인 표기 그대로 써. 예를 들어 PDF가 "싱글턴"이면 "싱글톤"으로 바꾸지 마.
- 모든 문장은 한국어 쉬운 말로 쓰고, 마크다운 기호(**, # 등)는 쓰지 마.
- 해당 내용이 없으면 빈 목록 []으로 둬.

아래 JSON 형식으로만 답해.
{
  "title": "노트 제목",
  "map": ["섹션 제목", "..."],
  "study_order": ["공부 순서 항목", "..."],
  "sections": [
    {
      "title": "슬라이드 주제",
      "pages": [3],
      "importance": 3,
      "link": "앞 섹션과 어떻게 이어지는지 한 문장",
      "why": "왜 필요했나",
      "so": "그래서 이게 나왔다",
      "analogy": "쉬운 비유 (PDF에 없는 내용)",
      "key_points": [{"text": "꼭 외울 것", "importance": 3}],
      "clues": [{"clue": "문제에 이런 문장이 보이면", "answer": "답"}],
      "traps": [{"text": "자주 틀리는 점", "importance": 2}],
      "definition": "서술형에 그대로 쓸 한 문장",
      "check": {"q": "확인 질문", "a": "정답"}
    }
  ],
  "review": {
    "comparisons": [
      {"title": "A vs B", "header": ["", "A", "B"], "rows": [["기준", "A의 특징", "B의 특징"]]}
    ]
  }
}

강의 PDF 내용:
"""

QUIZ_PROMPT = """너는 대학생의 시험공부를 돕는 조교야.
아래 강의 PDF 내용으로 복습 퀴즈 10문항을 만들어 줘.

순서
1. 먼저 이 범위에 나오는 개념을 concepts에 모두 적어. 용어는 PDF 표기 그대로, 근거 쪽 번호도 같이.
2. 그 개념들로 문제를 만들어.
3. 다 만든 뒤 모든 오답 보기를 다시 읽고, concepts에 없는 내용으로 된 보기는 고쳐.

문제 규칙
- 객관식 7문항, 단답형 3문항.
- 단순 암기만 묻지 말고, 개념을 이해했는지 확인하는 문제와 상황이나 코드를 보여 주고 어떤 개념인지 고르는 문제를 섞어.
- 객관식 보기는 4개이고, 정답 위치는 골고루 섞어.
- 용어는 PDF에 쓰인 표기 그대로 써. 예를 들어 PDF가 "싱글턴"이면 "싱글톤"으로 바꾸지 마.
- 모든 문제는 PDF 내용에 근거하고, pages에 근거 쪽 번호를 숫자로 적어. 쪽 번호는 내용 앞의 [n쪽] 표시를 따라.

오답 보기 규칙 (가장 중요)
- 오답 3개는 반드시 아래 두 방법 중 하나로만 만들어.
  가. concepts에 있는 다른 개념의 이름이나 설명 (헷갈리기 쉬운 짝을 우선)
  나. 정답 문장에서 한 부분만 틀리게 바꾼 문장 (숫자, 주체, 조건, "항상/절대" 같은 범위를 바꾸기)
- concepts에 없는 분야의 말은 오답에도 쓰지 마.
- 보기 4개의 길이와 말투를 비슷하게 맞춰. 정답만 길고 자세하면 안 돼.
- option_sources에는 보기마다 어디서 왔는지 적어. 정답은 "정답", 오답은 "가: 개념 이름 (p.4)" 또는 "나: 바꾼 부분"처럼.

좋은 예 (범위에 Context, Problem, Solution이 나올 때)
질문: "인스턴스가 여러 개면 일관성을 해친다"는 어느 구성 요소인가?
보기: Context / Problem / Solution / 패턴 이름
→ 오답이 모두 같은 범위의 개념이라, 개념을 구분해야 풀 수 있어.

나쁜 예
정의를 묻는 문제에 이 강의에 나오지 않는 다른 분야의 도구·규칙·기법을 오답으로 넣는 것.
→ 몰라도 소거법으로 풀려. 이런 보기가 떠오르면 concepts에서 다른 개념을 골라.

답 칸 규칙
- answer_index는 객관식 정답 보기의 번호(1~4). 단답형은 0.
- answer_text는 정답 내용. 객관식은 정답 보기 글자 그대로, 단답형은 짧은 정답(단어나 짧은 구).
- explanation은 정답인 이유와, 가장 헷갈리는 오답이 왜 틀렸는지를 한두 문장으로.
- importance는 1~3 숫자야. 3이 시험 1순위.
- 모든 문장은 한국어로 쓰고, 마크다운 기호(**, # 등)는 쓰지 마.
- 문제에 코드가 필요하면 question에 넣지 말고 code 칸에 줄바꿈을 살려서 따로 써. 코드가 없으면 code는 빈 문자열 ""로 둬.

아래 JSON 형식으로만 답해. 단답형은 options와 option_sources를 빈 목록 []으로 둬.
{
  "concepts": [{"term": "Context", "pages": [4]}],
  "questions": [
    {
      "section": "관련 섹션 제목",
      "type": "choice 또는 short",
      "question": "문제",
      "code": "",
      "code_language": "java",
      "options": ["보기1", "보기2", "보기3", "보기4"],
      "option_sources": ["가: Context (p.4)", "정답", "가: Solution (p.4)", "나: 주체를 바꿈"],
      "answer_index": 2,
      "answer_text": "정답",
      "explanation": "정답인 이유와 헷갈리는 오답이 틀린 이유",
      "pages": [4],
      "importance": 3
    }
  ]
}
"""


def note_prompt(pdf_text: str) -> str:
    """정리본 프롬프트에 오늘 범위 PDF 내용을 붙인다."""
    return SUMMARY_PROMPT + pdf_text


def quiz_prompt(pdf_text: str, sections=()) -> str:
    """퀴즈 프롬프트를 만든다. 정리본 섹션 이름을 주면 퀴즈의 section 칸을 그 이름에 맞춘다."""
    hint = ""
    if sections:
        hint = "\nsection 칸에는 다음 섹션 제목 중 하나를 그대로 써: " + ", ".join(sections) + "\n"
    return QUIZ_PROMPT + hint + "\n강의 PDF 내용:\n" + pdf_text


EXPLAIN_PROMPT = """너는 대학생의 시험공부를 돕는 친절한 조교야.
학생이 아래 단원을 "이해 안 돼요"라고 눌렀어. 강의 PDF 내용을 바탕으로 더 쉽게 다시 설명해 줘.

규칙
- 정리본을 그대로 반복하지 말고, 처음 듣는 사람도 알 수 있게 다른 말로 풀어.
- 내용은 강의 PDF에 근거해. 비유만 자료 밖 내용이어도 돼.
- 용어는 PDF에 쓰인 표기 그대로 써. 예를 들어 PDF가 "싱글턴"이면 "싱글톤"으로 바꾸지 마.
- 학생이 틀린 문제가 있으면 왜 그 답이 아닌지도 짚어 줘.
- 각 칸은 1~3문장으로 짧게. 한국어로 쓰고 마크다운 기호(**, # 등)는 쓰지 마.

아래 JSON 형식으로만 답해. 해당 내용이 없으면 빈 문자열 ""로 둬.
{
  "easy": "쉽게 말하면",
  "example": "강의에 나온 예나 구체적인 상황으로 보면",
  "analogy": "일상 비유 (자료 밖)",
  "confusion": "가장 헷갈리는 지점과 구분하는 법",
  "point": "시험에서는 이것만 기억"
}
"""


def explain_prompt(section: dict, pdf_text: str, question: str = "", answer: str = "", my_answer: str = "") -> str:
    """'이해 안 돼요'를 누른 단원(과 틀린 문제)을 더 쉽게 설명해 달라는 프롬프트."""
    import json
    keep = {k: section.get(k) for k in ("title", "why", "so", "key_points", "traps", "definition") if section.get(k)}
    extra = ""
    if question:
        extra = f"\n학생이 헷갈린 문제: {question}\n정답: {answer}\n학생의 답: {my_answer or '(모름)'}\n"
    return (EXPLAIN_PROMPT + "\n단원 정리본:\n" + json.dumps(keep, ensure_ascii=False)
            + extra + "\n강의 PDF 내용:\n" + pdf_text)

