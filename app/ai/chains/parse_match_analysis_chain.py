import json

from langchain_core.prompts import ChatPromptTemplate

from app.ai.context_builders.match_analysis_context import (
    build_candidate_profile_data,
    build_resume_analysis_data,
    build_resume_sections_data,
    build_vacancy_analysis_data,
    build_vacancy_data,
)
from app.ai.llm_executor import invoke_structured_llm
from app.ai.prompts.match_analysis import (
    MATCH_ANALYSIS_SYSTEM_PROMPT,
    MATCH_ANALYSIS_USER_PROMPT,
)
from app.models.candidate_profile import CandidateProfile
from app.models.resume import ResumeSection
from app.models.resume_analysis import ResumeAnalysis
from app.models.vacancy import Vacancy, VacancyAnalysis
from app.schemas.ai_outputs import ParsedMatchAnalysis


async def parse_match_analysis_chain(
    candidate_profile: CandidateProfile,
    resume_analysis: ResumeAnalysis,
    resume_sections: list[ResumeSection],
    vacancy: Vacancy,
    vacancy_analysis: VacancyAnalysis,
    resume_text: str,
    vacancy_text: str,
) -> ParsedMatchAnalysis:
    """Analyze how well a resume matches a vacancy."""

    candidate_profile_json = json.dumps(
        build_candidate_profile_data(candidate_profile),
        ensure_ascii=False,
        indent=2,
    )

    resume_analysis_json = json.dumps(
        build_resume_analysis_data(resume_analysis),
        ensure_ascii=False,
        indent=2,
    )

    resume_sections_json = json.dumps(
        build_resume_sections_data(resume_sections),
        ensure_ascii=False,
        indent=2,
    )

    vacancy_json = json.dumps(
        build_vacancy_data(vacancy),
        ensure_ascii=False,
        indent=2,
    )

    vacancy_analysis_json = json.dumps(
        build_vacancy_analysis_data(vacancy_analysis),
        ensure_ascii=False,
        indent=2,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", MATCH_ANALYSIS_SYSTEM_PROMPT),
            ("user", MATCH_ANALYSIS_USER_PROMPT),
        ]
    )

    return await invoke_structured_llm(
        prompt=prompt,
        input_data={
            "resume_analysis_json": resume_analysis_json,
            "resume_sections_json": resume_sections_json,
            "candidate_profile_json": candidate_profile_json,
            "vacancy_json": vacancy_json,
            "vacancy_analysis_json": vacancy_analysis_json,
            "resume_text": resume_text,
            "vacancy_text": vacancy_text,
        },
        output_schema=ParsedMatchAnalysis,
        temperature=0,
        error_message=(
            "Failed to parse match analysis into structured output"
        ),
    )