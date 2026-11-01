"""시험일까지 공부 범위를 하루씩 나누는 함수."""
from datetime import date, timedelta


def make_plan(total_pages: int, start_date: date, exam_date: date, reserve_final: bool = False) -> list[dict]:
    """공부 시작일부터 시험 전날까지 페이지를 하루씩 고르게 나눈다.
    reserve_final이면 시험 전날은 새 범위 없이 총정리 날로 비워 둔다 (공부할 날이 이틀 이상일 때만)."""
    span = (exam_date - start_date).days
    if reserve_final and span >= 2:
        span -= 1
    days = min(span, total_pages)
    if days <= 0:
        return []
    base, extra = divmod(total_pages, days)
    plan, page = [], 1
    for d in range(days):
        count = base + (1 if d < extra else 0)
        plan.append({"day": d + 1, "date": start_date + timedelta(days=d),
                     "start": page, "end": page + count - 1})
        page += count
    return plan
