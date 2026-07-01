from pydantic import BaseModel

class InterviewQuestionDTO(BaseModel):
    category: str
    question: str
    answer: str

class InterviewDeckDTO(BaseModel):
    thread_id: str
    status: str
    questions: list[InterviewQuestionDTO]
