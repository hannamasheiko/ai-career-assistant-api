from app.schemas.ai_outputs import ParsedCandidateProfile, ParsedResume, ParsedResumeSection


async def parse_resume_chain(raw_text: str) -> ParsedResume:
    """Parse raw resume text into structured candidate profile and resume sections.

    Temporary mock implementation.
    Later this function will be replaced with a real LangChain/OpenAI chain.
    """

    return ParsedResume(
        candidate_profile=ParsedCandidateProfile(
            full_name="Unknown Candidate",
            target_role="Python Developer",
            experience_level="Junior",
            years_of_experience=None,
            english_level=None,
            location=None,
            desired_salary_min=None,
            skills=["Python", "FastAPI", "PostgreSQL"],
            summary="Candidate profile extracted from raw resume text.",
        ),
        sections=[
            ParsedResumeSection(
                section_type="raw_resume",
                title="Raw Resume",
                content=raw_text,
                order_index=0,
            )
        ],
    )