"""Search queries for one research target."""

# How each subject is usually written in JAMB past-question titles.
SEARCH_NAMES = {
    "english-language": ["Use of English", "English Language"],
    "financial-accounting": ["Principles of Accounts", "Accounting"],
    "christian-religious-studies": ["CRS", "Christian Religious Studies"],
    "islamic-studies": ["IRS", "Islamic Studies"],
    "agricultural-science": ["Agricultural Science"],
    "literature-in-english": ["Literature in English"],
}


def queries_for(subject_name: str, subject_slug: str, year: int, exam: str = "JAMB") -> list[str]:
    names = SEARCH_NAMES.get(subject_slug, [subject_name])
    out = []
    for name in names:
        out += [
            f"{exam} {name} past questions {year} PDF",
            f"{exam} {name} past questions {year} with answers",
            f"UTME {name} {year} questions and answers",
        ]
    # de-duplicate, keep order
    return list(dict.fromkeys(out))
