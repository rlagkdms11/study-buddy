import json
import time

import streamlit as st
from google import genai
from google.genai import errors, types

# 앞에서부터 시도하고, 서버가 바쁘면 다음 모델로 넘어간다
MODELS = [
    "gemini-3.8-flash",
    "여기에_복사한_flash-lite_모델_이름",
]


def ask_ai(prompt: str, retries: int = 3, as_json: bool = False):
    """AI에게 질문하고 답을 받는다. 바쁘면 기다렸다 재시도하고, 그래도 안 되면 다음 모델로 넘어간다."""
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    config = types.GenerateContentConfig(response_mime_type="application/json") if as_json else None
    last_error = None
    for model in MODELS:
        for attempt in range(retries):
            try:
                response = client.models.generate_content(model=model, contents=prompt, config=config)
                return json.loads(response.text) if as_json else response.text
            except errors.ServerError as e:
                last_error = e
                time.sleep(2 ** attempt)  # 1초, 2초, 4초 기다렸다 다시
    raise last_error  # 모든 모델이 실패하면 그때 오류를 알린다