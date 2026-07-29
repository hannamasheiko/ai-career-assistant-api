from enum import StrEnum


class InteractionType(StrEnum):
    RESUME_SENT = "resume_sent"

    MESSAGE = "message"
    CALL = "call"

    SCREENING_QUESTIONS = "screening_questions"

    INTERVIEW_INVITATION = "interview_invitation"
    HR_INTERVIEW = "hr_interview"
    TECHNICAL_INTERVIEW = "technical_interview"
    FINAL_INTERVIEW = "final_interview"

    TEST_TASK = "test_task"

    FEEDBACK = "feedback"

    OFFER_DISCUSSION = "offer_discussion"
    OFFER = "offer"

    REJECTION = "rejection"


class InteractionDirection(StrEnum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"