# Architecture

```text
Browser (HTML/CSS/JavaScript)
        |
        | JSON over same-origin HTTP
        v
Flask REST API (Python)
   |                 |
   v                 v
MongoDB          SQLite reporting mirror
(users, profiles,  (JOIN/GROUP BY reports)
 internships,
 applications)
        |
        v
Skill-match service
(normalized skill overlap + ranked recommendations)
```

## Main MongoDB documents
- `users`: name, email, password_hash, role, created_at
- `student_profiles`: user_id, skills[], interests, education, resume_url
- `internships`: title, description, required_skills[], location, company_id, company_name, active
- `applications`: student_id, internship_id, status, applied_at, skills_at_application[]

## Match score
`score = matched_required_skills / total_required_skills * 100`
This is an explainable baseline and should not be presented as a trained predictive model.
