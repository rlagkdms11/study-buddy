import json
import time

import streamlit as st
from google import genai
from google.genai import errors, types

# 앞에서부터 시도하고, 서버가 바쁘거나 쓸 수 없으면 다음 모델로 넘어간다
MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
]


def ask_ai(prompt: str, retries: int = 3, as_json: bool = False):
    """AI에게 질문하고 답을 받는다.
    서버가 바쁘면(503) 기다렸다 재시도하고, 그래도 안 되면 다음 모델로 넘어간다.
    모델을 쓸 수 없으면(400, 404, 429 등) 재시도 없이 바로 다음 모델로 넘어간다.
    """
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    config = types.GenerateContentConfig(
        response_mime_type="application/json" if as_json else None,
        # 생각하는 단계를 낮춰서 속도를 높인다
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    )
    last_error = None
    for model in MODELS:
        for attempt in range(retries):
            start = time.perf_counter()
            try:
                response = client.models.generate_content(model=model, contents=prompt, config=config)
                print(f"[성공] {model} {time.perf_counter() - start:.0f}초")
                return json.loads(response.text) if as_json else response.text
            except errors.ServerError as e:
                last_error = e
                print(f"[재시도] {model} {attempt + 1}번째 실패 ({time.perf_counter() - start:.0f}초): 서버 혼잡")
                time.sleep(2 ** attempt)
            except errors.ClientError as e:
                last_error = e
                print(f"[건너뜀] {model}: {e.code} {e.message}")
                break  # 이 모델은 재시도해도 소용없으니 다음 모델로
    raise last_error  # 모든 모델이 실패하면 그때 오류를 알린다