# study-buddy

강의 PDF를 넣으면 정리본을 만들고, 시험일까지 하루 분량을 나눠 주고,
망각곡선에 맞춰 복습 퀴즈를 내주는 학습 도구입니다.

## 왜 만들었나
시험 기간마다 벼락치기를 반복했습니다.
강의 정리는 정리 앱, 문제 풀이는 퀴즈 앱으로 따로 써야 했고,
배운 내용을 잊을 때쯤 다시 복습하도록 도와주는 도구는 찾기 어려웠습니다.
그래서 강의 PDF 하나로 정리, 학습 계획, 망각곡선 복습, 퀴즈까지
한곳에서 할 수 있는 도구를 직접 만들어 보기로 했습니다.

## 기능 계획

### 필수
- [ ] PDF → 정리본 + 퀴즈 생성 ([#2](https://github.com/rlagkdms11/study-buddy/issues/2))
- [ ] 시험일 입력 → 하루 학습 분량 안내 ([#3](https://github.com/rlagkdms11/study-buddy/issues/3))
- [ ] 정리본 "이해 안 돼요" 설명 기능 ([#4](https://github.com/rlagkdms11/study-buddy/issues/4))
- [ ] 망각곡선 복습 일정 + 누적 퀴즈 ([#5](https://github.com/rlagkdms11/study-buddy/issues/5))

### 추가
- [ ] 학습 모드 자동 전환: 처음 배우기 ↔ 벼락치기 ([#6](https://github.com/rlagkdms11/study-buddy/issues/6))
- [ ] 빈칸 모드 ([#7](https://github.com/rlagkdms11/study-buddy/issues/7))

### 아이디어
- [ ] 정리본 스타일 선택: 필기 / 깔끔 ([#8](https://github.com/rlagkdms11/study-buddy/issues/8))

## 기술 스택
- Python, FastAPI (웹 버전 백엔드) · Streamlit (첫 버전)
- PyMuPDF (PDF 텍스트 추출)
- LLM API (정리본, 퀴즈, 설명 생성)

## 실행 방법
```bash
git clone https://github.com/rlagkdms11/study-buddy.git
cd study-buddy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# API 키는 .streamlit/secrets.toml의 GEMINI_API_KEY 또는 환경 변수 GEMINI_API_KEY에 넣기

# 웹 버전 백엔드 (만드는 중) — http://127.0.0.1:8000/docs 에서 API 확인
uvicorn server.main:app --reload

# 첫 버전 (Streamlit)
streamlit run app.py
```

## 폴더 구조
```
core/     PDF 글자 추출, 학습 계획, 프롬프트, AI 호출 (공통 코드)
server/   FastAPI 백엔드
app.py    Streamlit 첫 버전 화면
render.py Streamlit용 정리본·퀴즈 그리기
```

## 개발 기록
[docs/devlog.md](docs/devlog.md)
