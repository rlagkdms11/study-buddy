import time

import streamlit as st
from google import genai
from google.genai import errors

MODEL = "gemini-3.8-flash"


def ask_ai(prompt: str, retries: int = 3) -> str:
    """AI에게 질문하고 답을 글자로 받는다. 서버가 바쁘면 잠깐 기다렸다 다시 시도한다."""
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    for attempt in range(retries):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            return response.text
        except errors.ServerError:
            if attempt == retries - 1:  # 마지막 시도까지 실패하면 포기
                raise
            time.sleep(2 ** attempt)  # 1초, 2초 기다렸다 다시