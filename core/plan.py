"""시험일까지 공부 범위를 하루씩 나누는 함수."""
from datetime import date, timedelta


def make_plan(total_pages: int, start_date: date, exam_date: date) -> list[dict]:
    """공부 시작일부터 시험 전날까지 페이지를 하루씩 고르게 나눈다."""
    days = min((exam_date - start_date).days, total_pages)
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
