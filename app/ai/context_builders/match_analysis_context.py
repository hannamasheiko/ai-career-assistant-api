from app.models.resume import ResumeSection
from app.models.resume_analysis import ResumeAnalysis
from app.models.vacancy import Vacancy, VacancyAnalysis


def build_resume_analysis_data(
    resume_analysis: ResumeAnalysis,
) -> dict:
    """Build structured resume analysis data for match analysis."""

    return {
        "full_name": resume_analysis.full_name,
        "target_role": resume_analysis.target_role,
        "years_of_experience": (
            float(resume_analysis.years_of_experience)
            if resume_analysis.years_of_experience is not None
            else None
        ),
        "english_level": resume_analysis.english_level,
        "location": resume_analysis.location,
        "skills": resume_analysis.skills,
        "summary": resume_analysis.summary,
        "education_level": resume_analysis.education_level,
        "education_summary": resume_analysis.education_summary,
        "languages": resume_analysis.languages,
    }


def build_resume_sections_data(
    resume_sections: list[ResumeSection],
) -> list[dict]:
    """Build structured resume sections data for match analysis."""

    sorted_sections = sorted(
        resume_sections,
        key=lambda section: section.order_index,
    )

    return [
        {
            "section_type": section.section_type,
            "title": section.title,
            "content": section.content,
            "order_index": section.order_index,
        }
        for section in sorted_sections
    ]


def build_vacancy_data(
    vacancy: Vacancy,
) -> dict:
    """Build structured vacancy data for match analysis."""

    return {
        "company_name": vacancy.company_name,
        "position_title": vacancy.position_title,
        "location": vacancy.location,
        "work_format": vacancy.work_format,
        "employment_type": vacancy.employment_type,
        "salary_min": vacancy.salary_min,
        "salary_max": vacancy.salary_max,
        "currency": vacancy.currency,
    }


def build_vacancy_analysis_data(
    vacancy_analysis: VacancyAnalysis,
) -> dict:
    """Build structured vacancy analysis data for match analysis."""

    return {
        "experience_level": vacancy_analysis.experience_level,
        "english_level": vacancy_analysis.english_level,
        "required_skills": vacancy_analysis.required_skills,
        "optional_skills": vacancy_analysis.optional_skills,
        "responsibilities": vacancy_analysis.responsibilities,
        "red_flags": vacancy_analysis.red_flags,
        "green_flags": vacancy_analysis.green_flags,
        "summary": vacancy_analysis.summary,
        "recommendation": vacancy_analysis.recommendation,
    }