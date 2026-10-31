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


def note_prompt(pdf_text: str) -> str:
    """정리본 프롬프트에 오늘 범위 PDF 내용을 붙인다."""
    return SUMMARY_PROMPT + pdf_text


def quiz_prompt(pdf_text: str, sections=()) -> str:
    """퀴즈 프롬프트를 만든다. 정리본 섹션 이름을 주면 퀴즈의 section 칸을 그 이름에 맞춘다."""
    hint = ""
    if sections:
        hint = "\nsection 칸에는 다음 섹션 제목 중 하나를 그대로 써: " + ", ".join(sections) + "\n"
    return QUIZ_PROMPT + hint + "\n강의 PDF 내용:\n" + pdf_text
