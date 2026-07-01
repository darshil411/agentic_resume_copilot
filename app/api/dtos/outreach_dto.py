from pydantic import BaseModel

class OutreachCardDTO(BaseModel):
    type: str
    subject: str
    body: str

class OutreachWorkspaceDTO(BaseModel):
    thread_id: str
    status: str
    cold_emails: list[OutreachCardDTO]
    referrals: list[OutreachCardDTO]
    followups: list[OutreachCardDTO]
