from pydantic import BaseModel
from typing import List

class QuizItem(BaseModel):
    question: str
    options: List[str]
    answer: str

class OnboardingModule(BaseModel):
    requirement_id: str
    module_name: str
    mandatory: str
    source_doc_id: str
    source_section: str
    priority: str
    due_stage: str
    tasks: List[str]
    quiz: List[QuizItem]
    assessment_topic: str

class OnboardingPlan(BaseModel):
    employee_id: str = ""
    role: str = ""
    modules: List[OnboardingModule]
