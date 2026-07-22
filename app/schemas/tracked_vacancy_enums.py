from enum import StrEnum


class TrackedVacancyStatus(StrEnum):
    SAVED = "saved"
    ANALYZED = "analyzed"
    RESUME_SENT = "resume_sent"
    RECRUITER_CONTACT = "recruiter_contact"
    SCREENING = "screening"
    INTERVIEW = "interview"
    TEST_TASK = "test_task"
    OFFER = "offer"
    REJECTED = "rejected"
    DISCARDED = "discarded"
    CLOSED = "closed"


class TrackedVacancyPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TrackedVacancyDecision(StrEnum):
    INTERESTED = "interested"
    CONSIDER_LATER = "consider_later"
    NOT_INTERESTED = "not_interested"
