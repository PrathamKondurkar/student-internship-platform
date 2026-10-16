from backend.services.matching import calculate_match, normalize_skills, rank_internships


def test_calculate_match_percentage_and_missing_skills():
    result = calculate_match(["Python", "SQL", "python"], ["python", "MongoDB", "SQL", "Flask"])
    assert result["score"] == 50
    assert result["matched_skills"] == ["python", "sql"]
    assert result["missing_skills"] == ["flask", "mongodb"]


def test_empty_requirements_do_not_divide_by_zero():
    result = calculate_match(["Python"], [])
    assert result["score"] == 0
    assert result["missing_skills"] == []


def test_normalize_skills_ignores_blanks():
    assert normalize_skills([" Python ", "", None, "SQL"]) == {"python", "sql"}


def test_rank_internships_highest_match_first():
    internships = [
        {"title": "A", "required_skills": ["Python", "SQL"]},
        {"title": "B", "required_skills": ["Python", "SQL", "MongoDB"]},
    ]
    ranked = rank_internships(["Python", "SQL"], internships)
    assert ranked[0]["title"] == "A"
    assert ranked[0]["match"]["score"] == 100
