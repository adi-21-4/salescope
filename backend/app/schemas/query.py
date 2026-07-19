from pydantic import BaseModel, Field


class NLQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class NLDataPoint(BaseModel):
    label: str
    value: float


class NLQueryResponse(BaseModel):
    answer_text: str
    data: list[NLDataPoint]
    chart_type: str
