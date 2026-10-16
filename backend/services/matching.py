from collections.abc import Iterable


def normalize_skills(skills: Iterable[str] | None) -> set[str]:
    if not skills:
        return set()
    return {str(skill).strip().lower() for skill in skills if str(skill).strip()}


def calculate_match(student_skills: Iterable[str], required_skills: Iterable[str]) -> dict:
    student = normalize_skills(student_skills)
    required = normalize_skills(required_skills)
    matched = sorted(student & required)
    missing = sorted(required - student)
    score = round((len(matched) / len(required)) * 100) if required else 0
    return {
        "score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "required_skill_count": len(required),
    }


def rank_internships(student_skills: Iterable[str], internships: list[dict]) -> list[dict]:
    ranked = []
    for internship in internships:
        result = calculate_match(student_skills, internship.get("required_skills", []))
        ranked.append({**internship, "match": result})
    return sorted(ranked, key=lambda item: item["match"]["score"], reverse=True)
