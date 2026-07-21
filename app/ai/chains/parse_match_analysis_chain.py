import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.ai.context_builders.match_analysis_context import (
    build_candidate_profile_data,
    build_resume_analysis_data,
    build_resume_sections_data,
    build_vacancy_analysis_data,
    build_vacancy_data,
)
from app.core.config import settings
from app.models.candidate_profile import CandidateProfile
from app.models.resume import ResumeSection
from app.models.resume_analysis import ResumeAnalysis
from app.models.vacancy import Vacancy, VacancyAnalysis
from app.schemas.ai_outputs import ParsedMatchAnalysis
from app.services.openai_cost_tracker import print_openai_usage

from app.ai.prompts.match_analysis import (
    MATCH_ANALYSIS_PROMPT_VERSION,
    MATCH_ANALYSIS_SYSTEM_PROMPT,
    MATCH_ANALYSIS_USER_PROMPT,
)


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

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

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

    prompt=ChatPromptTemplate.from_messages(
        [
            ("system", MATCH_ANALYSIS_SYSTEM_PROMPT),
            ("user", MATCH_ANALYSIS_USER_PROMPT),
        ]
    )

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    structured_llm = llm.with_structured_output(
        ParsedMatchAnalysis,
        include_raw=True,
    )

    chain = prompt | structured_llm

    result = await chain.ainvoke(
        {
            "resume_analysis_json": resume_analysis_json,
            "resume_sections_json": resume_sections_json,
            "candidate_profile_json": candidate_profile_json,
            "vacancy_json": vacancy_json,
            "vacancy_analysis_json": vacancy_analysis_json,
            "resume_text": resume_text,
            "vacancy_text": vacancy_text,
        }
    )

    parsed_match_analysis = result["parsed"]
    raw_response = result["raw"]

    if parsed_match_analysis is None:
        raise RuntimeError(
            "Failed to parse match analysis into structured output"
        )

    usage_metadata = getattr(
        raw_response,
        "usage_metadata",
        None,
    )

    if usage_metadata:
        input_tokens = usage_metadata.get(
            "input_tokens",
            0,
        )
        output_tokens = usage_metadata.get(
            "output_tokens",
            0,
        )
        total_tokens = usage_metadata.get(
            "total_tokens",
            0,
        )

        print_openai_usage(
            model=settings.openai_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    return parsed_match_analysis