from __future__ import annotations

import re

from config import settings
from elastic_service import client, get_degree


TERM_ORDER = ["term 1", "term 2", "term 3"]
TERM_RANK = {label: idx for idx, label in enumerate(TERM_ORDER)}
COURSE_CODE_RE = re.compile(r"[A-Z]{4}\d{4}")
DEFAULT_ENROLLMENT_YEAR = 2026
DEFAULT_START_TERM = "term 1"
DEFAULT_DEGREE_ID = "3707-SENGAH"
FEE_PLAN_OPTIONS = frozenset({"hecs", "domestic", "international"})
DEGREE_CODE_ALIASES = {
    "SENG4920": "COMP4920",
}
GEN_ED_UOC = 12
GEN_ED_PLACEHOLDERS = [
    {
        "course_code": "GENED0001",
        "title": "General Education Placeholder 1",
        "uoc": 6,
    },
    {
        "course_code": "GENED0002",
        "title": "General Education Placeholder 2",
        "uoc": 6,
    },
]


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _normalize_degree_course_code(raw_code: object) -> str:
    code = str(raw_code).strip().upper()
    return DEGREE_CODE_ALIASES.get(code, code)


def _normalize_term(value: str) -> str | None:
    token = value.strip().lower().replace("-", " ")
    token = re.sub(r"\s+", " ", token)
    aliases = {
        "t1": "term 1",
        "term1": "term 1",
        "1": "term 1",
        "t2": "term 2",
        "term2": "term 2",
        "2": "term 2",
        "t3": "term 3",
        "term3": "term 3",
        "3": "term 3",
    }
    if token in TERM_ORDER:
        return token
    return aliases.get(token)


def _parse_semester_offerings(semester_field: object) -> set[str]:
    if semester_field is None:
        return set(TERM_ORDER)

    raw_values: list[str] = []
    if isinstance(semester_field, str):
        raw_values.extend(re.split(r"[,/;|]", semester_field))
    elif isinstance(semester_field, list):
        for item in semester_field:
            if isinstance(item, str):
                raw_values.extend(re.split(r"[,/;|]", item))

    parsed = {
        term
        for token in raw_values
        for term in [_normalize_term(token)]
        if term is not None
    }
    return parsed or set(TERM_ORDER)


def _course_uoc(course: dict) -> int:
    return _to_int(course.get("uoc"), default=6)


def _course_fee(course: dict, fee_type: str = "hecs") -> float:
    def parse_fee(raw: object) -> float | None:
        if raw is None:
            return None
        token = str(raw).strip()
        if not token:
            return None
        token = token.replace("$", "").replace(",", "")
        try:
            return float(token)
        except ValueError:
            return None

    fees = course.get("fees")
    if isinstance(fees, dict):
        other_keys = [k for k in ("hecs", "domestic", "international") if k != fee_type]
        for key in [fee_type] + other_keys:
            parsed = parse_fee(fees.get(key))
            if parsed is not None:
                return parsed

    parsed_top_level = parse_fee(course.get("course_fee"))
    if parsed_top_level is not None:
        return parsed_top_level

    return 999999.0


def _course_offered_in_term(course: dict, term: str) -> bool:
    offerings = _parse_semester_offerings(course.get("semester"))
    return term in offerings


def _tokenize_enrolment_rule(rule: str) -> list[str]:
    tokens = re.findall(r"[A-Z]{4}\d{4}|AND|OR|\(|\)", rule.upper())
    return tokens


def _to_rpn(tokens: list[str]) -> list[str]:
    precedence = {"OR": 1, "AND": 2}
    output: list[str] = []
    operators: list[str] = []

    prev_was_operand = False
    for token in tokens:
        is_operand = bool(COURSE_CODE_RE.fullmatch(token))
        if is_operand:
            if prev_was_operand:
                # Adjacent course codes are treated as OR alternatives.
                while operators and operators[-1] in precedence:
                    if precedence[operators[-1]] >= precedence["OR"]:
                        output.append(operators.pop())
                    else:
                        break
                operators.append("OR")
            output.append(token)
            prev_was_operand = True
            continue

        if token in precedence:
            while operators and operators[-1] in precedence:
                if precedence[operators[-1]] >= precedence[token]:
                    output.append(operators.pop())
                else:
                    break
            operators.append(token)
            prev_was_operand = False
            continue

        if token == "(":
            operators.append(token)
            prev_was_operand = False
            continue

        if token == ")":
            while operators and operators[-1] != "(":
                output.append(operators.pop())
            if operators and operators[-1] == "(":
                operators.pop()
            prev_was_operand = True

    while operators:
        top = operators.pop()
        if top != "(":
            output.append(top)

    return output


def _evaluate_rpn(rpn: list[str], done_codes: set[str]) -> bool | None:
    stack: list[bool] = []
    for token in rpn:
        if COURSE_CODE_RE.fullmatch(token):
            stack.append(token in done_codes)
            continue
        if token == "AND":
            if len(stack) < 2:
                return None
            right = stack.pop()
            left = stack.pop()
            stack.append(left and right)
            continue
        if token == "OR":
            if len(stack) < 2:
                return None
            right = stack.pop()
            left = stack.pop()
            stack.append(left or right)

    if len(stack) != 1:
        return None
    return stack[-1]


def _satisfies_enrolment_rules(course: dict, done_codes: set[str]) -> bool | None:
    rule = course.get("enrolment_rules")
    if not isinstance(rule, str) or not rule.strip():
        return None

    tokens = _tokenize_enrolment_rule(rule)
    if not any(COURSE_CODE_RE.fullmatch(tok) for tok in tokens):
        return None

    rpn = _to_rpn(tokens)
    return _evaluate_rpn(rpn, done_codes)


def _prereqs_satisfied(course: dict, done_codes: set[str]) -> bool:
    enrolment_ok = _satisfies_enrolment_rules(course, done_codes)
    if enrolment_ok is not None:
        return enrolment_ok

    raw = course.get("prerequisites", [])
    if isinstance(raw, list):
        prereq_codes = {
            str(item).strip().upper()
            for item in raw
            if COURSE_CODE_RE.fullmatch(str(item).strip().upper())
        }
        if not prereq_codes:
            return True
        # Treat prerequisites list as possible alternatives for MVP.
        return any(code in done_codes for code in prereq_codes)

    if isinstance(raw, str):
        codes = set(COURSE_CODE_RE.findall(raw.upper()))
        if not codes:
            return True
        return any(code in done_codes for code in codes)

    return True


def _build_term_sequence(enrollment_year: int, max_terms: int) -> list[tuple[int, str]]:
    start_year = enrollment_year
    start_rank = TERM_RANK[DEFAULT_START_TERM]

    terms: list[tuple[int, str]] = []
    year = start_year
    rank = start_rank
    for _ in range(max_terms):
        terms.append((year, TERM_ORDER[rank]))
        rank += 1
        if rank >= len(TERM_ORDER):
            rank = 0
            year += 1
    return terms


def _search_all_courses(size: int = 2000) -> list[dict]:
    response = client.search(
        index=settings.elastic_index,
        size=size,
        query={"match_all": {}},
    )
    hits = response.get("hits", {}).get("hits", [])
    courses: list[dict] = []
    for hit in hits:
        doc = hit.get("_source", {})
        code = doc.get("course_code")
        if isinstance(code, str) and code.strip():
            courses.append(doc)
    return courses


def _build_catalog() -> tuple[dict[str, dict], list[dict]]:
    courses = _search_all_courses()
    catalog = {}
    for course in courses:
        code = str(course.get("course_code", "")).strip().upper()
        if code:
            catalog[code] = course
    return catalog, courses


def list_degree_options() -> list[dict]:
    response = client.search(
        index=settings.elastic_degree_index,
        size=500,
        query={"match_all": {}},
    )
    hits = response.get("hits", {}).get("hits", [])
    options = []
    for hit in hits:
        src = hit.get("_source", {})
        options.append(
            {
                "degree_id": src.get("degree_id"),
                "degree_name": src.get("degree_name"),
                "program_code": src.get("program_code"),
                "specialisation_code": src.get("specialisation_code"),
            }
        )
    options.sort(key=lambda d: str(d.get("degree_name", "")))
    return options


def _extract_degree_requirements(degree: dict) -> dict:
    core_courses_raw = degree.get("core_courses", []) or []
    thesis_courses_raw = (degree.get("thesis", {}) or {}).get("courses", []) or []

    core_courses = []
    for item in core_courses_raw:
        if (
            isinstance(item, dict)
            and str(item.get("type", "")).strip().lower() == "oneof"
        ):
            options = item.get("courses", [])
            if isinstance(options, list) and options:
                first = _normalize_degree_course_code(options[0])
                if COURSE_CODE_RE.fullmatch(first):
                    core_courses.append(first)
                    continue
        if isinstance(item, dict) and item.get("course_code"):
            core_courses.append(
                _normalize_degree_course_code(item["course_code"])
            )
        elif isinstance(item, str) and item.strip():
            core_courses.append(_normalize_degree_course_code(item))

    thesis_courses = []
    for item in thesis_courses_raw:
        if isinstance(item, dict) and item.get("course_code"):
            thesis_courses.append(
                _normalize_degree_course_code(item["course_code"])
            )
        elif isinstance(item, str) and item.strip():
            thesis_courses.append(_normalize_degree_course_code(item))

    core_uoc = _to_int(degree.get("core_uoc"), 0)
    thesis_uoc = _to_int((degree.get("thesis", {}) or {}).get("uoc"), 0)
    if not core_uoc:
        core_uoc = len(core_courses) * 6
    if not thesis_uoc:
        thesis_uoc = len(thesis_courses) * 4

    total_uoc = _to_int(degree.get("total_uoc"), 0)
    remaining_elective_uoc = _to_int(degree.get("remaining_elective_uoc"), 0)
    if not remaining_elective_uoc and total_uoc:
        remaining_elective_uoc = max(total_uoc - core_uoc - thesis_uoc, 0)

    duration_years = max(_to_int(degree.get("duration_years"), 4), 1)

    dedup_core = list(dict.fromkeys(core_courses))
    dedup_thesis = list(dict.fromkeys(thesis_courses))

    return {
        "core_courses": dedup_core,
        "thesis_courses": dedup_thesis,
        "core_uoc": core_uoc,
        "thesis_uoc": thesis_uoc,
        "remaining_elective_uoc": remaining_elective_uoc,
        "duration_years": duration_years,
    }


def _recommended_ranking(query: str) -> list[str]:
    if not query.strip():
        return []

    response = client.search(
        index=settings.elastic_index,
        size=100,
        query={
            "sparse_vector": {
                "field": "text_embedding.predicted_value",
                "inference_id": "my-elser-model",
                "query": query,
            }
        },
    )
    hits = response.get("hits", {}).get("hits", [])
    return [
        str(hit.get("_source", {}).get("course_code", "")).strip().upper()
        for hit in hits
        if str(hit.get("_source", {}).get("course_code", "")).strip()
    ]


def _initialize_plan_terms(terms: list[tuple[int, str]]) -> list[dict]:
    return [
        {"year": year, "term": term, "courses": [], "uoc": 0}
        for year, term in terms
    ]


def _append_course_to_term(term_bucket: dict, course: dict) -> None:
    term_bucket["courses"].append(course)
    term_bucket["uoc"] += _course_uoc(course)


def _append_placeholder_to_term(
    term_bucket: dict,
    course_code: str,
    title: str,
    uoc: int,
    category: str,
) -> None:
    course = {
        "course_code": course_code,
        "title": title,
        "uoc": uoc,
        "category": category,
        "placeholder": True,
    }
    term_bucket["courses"].append(course)
    term_bucket["uoc"] += uoc


def _compute_done_before_term(
    completed_courses: list[str],
    plan_terms: list[dict],
    term_index: int,
) -> set[str]:
    done = {code.strip().upper() for code in completed_courses}
    for idx in range(0, term_index):
        for course in plan_terms[idx].get("courses", []):
            if isinstance(course, dict):
                code = str(course.get("course_code", "")).strip().upper()
            else:
                code = str(course).strip().upper()
            if code:
                done.add(code)
    return done


def _planned_or_completed(
    completed_courses: list[str],
    plan_terms: list[dict],
) -> set[str]:
    planned = {
        str(course.get("course_code", "")).strip().upper()
        for term in plan_terms
        for course in term.get("courses", [])
        if isinstance(course, dict)
    }
    completed = {code.strip().upper() for code in completed_courses}
    return planned | completed


def _find_term_bucket(
    plan_terms: list[dict],
    year: int,
    term: str,
) -> dict | None:
    for bucket in plan_terms:
        if bucket.get("year") == year and bucket.get("term") == term:
            return bucket
    return None


def _schedule_course_any_term(
    code: str,
    catalog: dict[str, dict],
    plan_terms: list[dict],
    completed_courses: list[str],
    max_uoc_per_term: int,
    locked_terms: set[tuple[int, str]] | None = None,
) -> bool:
    course = catalog.get(code)
    if not course:
        return False

    done = _planned_or_completed(completed_courses, plan_terms)
    if code in done:
        return True

    for idx, bucket in enumerate(plan_terms):
        year = int(bucket.get("year", 0))
        term = str(bucket.get("term", ""))
        if locked_terms and (year, term) in locked_terms:
            continue
        if bucket["uoc"] + _course_uoc(course) > max_uoc_per_term:
            continue
        if not _course_offered_in_term(course, term):
            continue
        done_before = _compute_done_before_term(
            completed_courses,
            plan_terms,
            idx,
        )
        if not _prereqs_satisfied(course, done_before):
            continue

        _append_course_to_term(bucket, course)
        return True

    return False


def _schedule_placeholder_from_end(
    plan_terms: list[dict],
    course_code: str,
    title: str,
    uoc: int,
    max_uoc_per_term: int,
) -> bool:
    for bucket in reversed(plan_terms):
        if bucket["uoc"] + uoc > max_uoc_per_term:
            continue
        _append_placeholder_to_term(
            term_bucket=bucket,
            course_code=course_code,
            title=title,
            uoc=uoc,
            category="gen_ed",
        )
        return True
    return False


def _schedule_core_placeholder_from_end(
    plan_terms: list[dict],
    course_code: str,
    max_uoc_per_term: int,
) -> bool:
    for bucket in reversed(plan_terms):
        if bucket["uoc"] + 6 > max_uoc_per_term:
            continue
        _append_placeholder_to_term(
            term_bucket=bucket,
            course_code=course_code,
            title=f"Core Placeholder for {course_code}",
            uoc=6,
            category="core",
        )
        return True
    return False


def _fill_uoc_gap_with_placeholders(
    plan_terms: list[dict],
    missing_uoc: int,
    max_uoc_per_term: int,
) -> int:
    remaining = max(0, missing_uoc)
    placeholder_idx = 1
    while remaining > 0:
        block_uoc = 6 if remaining >= 6 else remaining
        scheduled = False
        for bucket in reversed(plan_terms):
            if bucket["uoc"] + block_uoc > max_uoc_per_term:
                continue
            _append_placeholder_to_term(
                term_bucket=bucket,
                course_code=f"ELCT{placeholder_idx:04d}",
                title="Elective Placeholder",
                uoc=block_uoc,
                category="elective",
            )
            scheduled = True
            placeholder_idx += 1
            remaining -= block_uoc
            break
        if not scheduled:
            break

    return remaining


def _schedule_course_specific_term(
    code: str,
    catalog: dict[str, dict],
    plan_terms: list[dict],
    completed_courses: list[str],
    target_year: int,
    target_term: str,
    max_uoc_per_term: int,
) -> bool:
    course = catalog.get(code)
    if not course:
        return False

    done = _planned_or_completed(completed_courses, plan_terms)
    if code in done:
        return True

    target_idx = -1
    for idx, bucket_candidate in enumerate(plan_terms):
        if (
            bucket_candidate.get("year") == target_year
            and bucket_candidate.get("term") == target_term
        ):
            target_idx = idx
            break

    bucket = _find_term_bucket(plan_terms, target_year, target_term)
    if not bucket:
        return False
    if bucket["uoc"] + _course_uoc(course) > max_uoc_per_term:
        return False
    if not _course_offered_in_term(course, target_term):
        return False
    if target_idx >= 0:
        done_before = _compute_done_before_term(
            completed_courses,
            plan_terms,
            target_idx,
        )
        if not _prereqs_satisfied(course, done_before):
            return False

    _append_course_to_term(bucket, course)
    return True


def _elective_candidates(
    mode: str,
    all_courses: list[dict],
    catalog: dict[str, dict],
    completed_courses: list[str],
    core_codes: set[str],
    thesis_codes: set[str],
    preferred_codes: list[str],
    fee_type: str = "hecs",
) -> list[str]:
    done = {code.strip().upper() for code in completed_courses}

    pool = []
    for course in all_courses:
        code = str(course.get("course_code", "")).strip().upper()
        if not code:
            continue
        if code in done or code in core_codes or code in thesis_codes:
            continue
        pool.append(code)

    if mode == "recommended":
        ordered = [code for code in preferred_codes if code in set(pool)]
        ordered += [code for code in pool if code not in set(ordered)]
        return ordered

    if mode == "cheapest":
        return sorted(
            pool,
            key=lambda code: _course_fee(catalog.get(code, {}), fee_type),
        )

    return pool


def _thesis_locked_terms(enrollment_year: int) -> list[tuple[int, str]]:
    year_4 = enrollment_year + 3
    return [
        (year_4, "term 1"),
        (year_4, "term 2"),
        (year_4, "term 3"),
    ]


def build_plan(
    degree_id: str,
    mode: str,
    enrollment_year: int = DEFAULT_ENROLLMENT_YEAR,
    completed_courses: list[str] | None = None,
    job_interest_query: str = "",
    fee_type: str = "hecs",
    max_uoc_per_term: int = 18,
    planning_horizon_terms: int = 24,
) -> dict:
    completed_courses = completed_courses or []
    degree = get_degree(degree_id)["degree"]
    req = _extract_degree_requirements(degree)
    catalog, all_courses = _build_catalog()

    terms = _build_term_sequence(enrollment_year, planning_horizon_terms)
    plan_terms = _initialize_plan_terms(terms)

    core_list = req["core_courses"]
    thesis_list = req["thesis_courses"]
    core_codes = set(core_list)
    thesis_codes = set(thesis_list)

    thesis_slots = _thesis_locked_terms(enrollment_year)
    thesis_slot_set = set(thesis_slots)

    remaining_core = list(core_list)
    while remaining_core:
        next_round = []
        progress = False
        for code in remaining_core:
            ok = _schedule_course_any_term(
                code=code,
                catalog=catalog,
                plan_terms=plan_terms,
                completed_courses=completed_courses,
                max_uoc_per_term=max_uoc_per_term,
                locked_terms=thesis_slot_set,
            )
            if ok:
                progress = True
            else:
                next_round.append(code)

        if not progress:
            remaining_core = next_round
            break
        remaining_core = next_round

    unscheduled_core = remaining_core

    core_placeholders = []
    still_unscheduled_core = []
    for code in unscheduled_core:
        if code in catalog:
            still_unscheduled_core.append(code)
            continue
        if _schedule_core_placeholder_from_end(
            plan_terms=plan_terms,
            course_code=code,
            max_uoc_per_term=max_uoc_per_term,
        ):
            core_placeholders.append(code)
        else:
            still_unscheduled_core.append(code)
    unscheduled_core = still_unscheduled_core

    unscheduled_thesis = []
    remaining_thesis = [
        code
        for code in thesis_list
        if code not in {c.strip().upper() for c in completed_courses}
    ]

    for idx, code in enumerate(remaining_thesis):
        if idx >= len(thesis_slots):
            unscheduled_thesis.append(code)
            continue
        year, term = thesis_slots[idx]
        ok = _schedule_course_specific_term(
            code=code,
            catalog=catalog,
            plan_terms=plan_terms,
            completed_courses=completed_courses,
            target_year=year,
            target_term=term,
            max_uoc_per_term=max_uoc_per_term,
        )
        if not ok:
            unscheduled_thesis.append(code)

    preferred = (
        _recommended_ranking(job_interest_query)
        if mode == "recommended"
        else []
    )

    gen_ed_target_uoc = GEN_ED_UOC
    elective_target_uoc = max(req["remaining_elective_uoc"] - gen_ed_target_uoc, 0)
    elective_codes = _elective_candidates(
        mode=mode,
        all_courses=all_courses,
        catalog=catalog,
        completed_courses=completed_courses,
        core_codes=core_codes,
        thesis_codes=thesis_codes,
        preferred_codes=preferred,
        fee_type=fee_type,
    )

    gained_elective = 0
    for code in elective_codes:
        if gained_elective >= elective_target_uoc:
            break

        ok = _schedule_course_any_term(
            code=code,
            catalog=catalog,
            plan_terms=plan_terms,
            completed_courses=completed_courses,
            max_uoc_per_term=max_uoc_per_term,
            locked_terms=None,
        )
        if ok:
            course = catalog.get(code, {})
            gained_elective += _course_uoc(course)

    elective_uoc_remaining = max(elective_target_uoc - gained_elective, 0)

    scheduled_gen_ed = 0
    for placeholder in GEN_ED_PLACEHOLDERS:
        ok = _schedule_placeholder_from_end(
            plan_terms=plan_terms,
            course_code=placeholder["course_code"],
            title=placeholder["title"],
            uoc=int(placeholder["uoc"]),
            max_uoc_per_term=max_uoc_per_term,
        )
        if ok:
            scheduled_gen_ed += int(placeholder["uoc"])

    gen_ed_uoc_remaining = max(gen_ed_target_uoc - scheduled_gen_ed, 0)

    total_gap = elective_uoc_remaining + gen_ed_uoc_remaining
    if total_gap > 0:
        leftover_after_fill = _fill_uoc_gap_with_placeholders(
            plan_terms=plan_terms,
            missing_uoc=total_gap,
            max_uoc_per_term=max_uoc_per_term,
        )
        # Prefer to treat any successful fallback as elective completion first.
        filled = total_gap - leftover_after_fill
        if filled > 0:
            fill_for_elective = min(filled, elective_uoc_remaining)
            elective_uoc_remaining -= fill_for_elective
            filled -= fill_for_elective
            fill_for_gen_ed = min(filled, gen_ed_uoc_remaining)
            gen_ed_uoc_remaining -= fill_for_gen_ed

    terms_out = [term for term in plan_terms if term["courses"]]
    unmet = {}
    if unscheduled_core:
        unmet["core_courses_unscheduled"] = unscheduled_core
    if core_placeholders:
        unmet["core_placeholders_added"] = core_placeholders
    if unscheduled_thesis:
        unmet["thesis_courses_unscheduled"] = unscheduled_thesis
    if elective_uoc_remaining > 0:
        unmet["elective_uoc_remaining"] = elective_uoc_remaining
    if gen_ed_uoc_remaining > 0:
        unmet["gen_ed_uoc_remaining"] = gen_ed_uoc_remaining

    return {
        "mode": mode,
        "degree_id": degree_id,
        "enrollment_year": enrollment_year,
        "start_term": DEFAULT_START_TERM,
        "fee_type": fee_type,
        "gen_ed_target_uoc": gen_ed_target_uoc,
        "elective_target_uoc": elective_target_uoc,
        "terms": terms_out,
        "thesis_locked_terms": [
            {"year": year, "term": term} for year, term in thesis_slots
        ],
        "unmet_requirements": unmet,
    }


def _term_key(year: int, term: str) -> tuple[int, int]:
    return year, TERM_RANK.get(term, 99)


def validate_manual_course_add(
    degree_id: str,
    existing_plan_terms: list[dict],
    target_year: int,
    target_term: str,
    course_code: str,
    enrollment_year: int = DEFAULT_ENROLLMENT_YEAR,
    completed_courses: list[str] | None = None,
) -> dict:
    completed_courses = completed_courses or []
    normalized_term = _normalize_term(target_term)
    if not normalized_term:
        return {
            "valid": False,
            "reason": "target_term must be one of term 1, term 2, or term 3",
        }

    req = _extract_degree_requirements(get_degree(degree_id)["degree"])
    catalog, _ = _build_catalog()

    course_code = course_code.upper().strip()
    course = catalog.get(course_code)
    if not course:
        return {
            "valid": False,
            "reason": f"Course {course_code} was not found in the courses index.",
        }

    if not _course_offered_in_term(course, normalized_term):
        return {
            "valid": False,
            "reason": f"{course_code} is not offered in {normalized_term}.",
        }

    completed_set = {code.upper() for code in completed_courses}
    already_planned = set()
    for term in existing_plan_terms:
        for entry in term.get("courses", []):
            if isinstance(entry, dict):
                code = str(entry.get("course_code", "")).strip().upper()
            else:
                code = str(entry).strip().upper()
            if code:
                already_planned.add(code)

    if course_code in completed_set or course_code in already_planned:
        return {
            "valid": False,
            "reason": f"{course_code} is already completed or already planned.",
        }

    sorted_terms = sorted(
        existing_plan_terms,
        key=lambda t: _term_key(
            _to_int(t.get("year"), 0),
            str(t.get("term", "")),
        ),
    )
    done_before = {code.upper() for code in completed_courses}
    target_key = _term_key(target_year, normalized_term)
    for term in sorted_terms:
        year = _to_int(term.get("year"), 0)
        term_name = _normalize_term(str(term.get("term", "")))
        if not term_name:
            continue
        if _term_key(year, term_name) >= target_key:
            continue
        for entry in term.get("courses", []):
            if isinstance(entry, dict):
                planned_code = str(entry.get("course_code", "")).strip().upper()
            else:
                planned_code = str(entry).strip().upper()
            if planned_code:
                done_before.add(planned_code)

    if not _prereqs_satisfied(course, done_before):
        return {
            "valid": False,
            "reason": "Prerequisites/enrolment rules are not satisfied.",
        }

    thesis_codes = set(req["thesis_courses"])
    if course_code in thesis_codes:
        allowed = set(_thesis_locked_terms(enrollment_year))
        if (target_year, normalized_term) not in allowed:
            return {
                "valid": False,
                "reason": (
                    "Thesis courses must be placed in the final-year "
                    "term 1, term 2, or term 3 slots."
                ),
            }
        contribution = ["counts_as_thesis"]
    elif course_code in set(req["core_courses"]):
        contribution = ["counts_as_core"]
    else:
        contribution = ["counts_as_elective"]

    return {
        "valid": True,
        "course_code": course_code,
        "target_year": target_year,
        "target_term": normalized_term,
        "contribution": contribution,
    }


def _search_course_codes_from_query(course_query: str) -> list[str]:
    query = course_query.strip()
    if not query:
        return []

    ranked_codes = _recommended_ranking(query)
    response = client.search(
        index=settings.elastic_index,
        size=25,
        query={
            "multi_match": {
                "query": query,
                "fields": ["course_code^4", "title^3", "description", "tags"],
            }
        },
    )
    lexical_codes = [
        str(hit.get("_source", {}).get("course_code", "")).strip().upper()
        for hit in response.get("hits", {}).get("hits", [])
        if str(hit.get("_source", {}).get("course_code", "")).strip()
    ]

    merged = []
    seen = set()
    for code in ranked_codes + lexical_codes:
        if code and code not in seen:
            seen.add(code)
            merged.append(code)
    return merged


def suggest_manual_course_for_slot(
    degree_id: str,
    existing_plan_terms: list[dict],
    target_year: int,
    target_term: str,
    course_query: str,
    enrollment_year: int = DEFAULT_ENROLLMENT_YEAR,
    completed_courses: list[str] | None = None,
) -> dict:
    completed_courses = completed_courses or []
    candidates = _search_course_codes_from_query(course_query)
    if not candidates:
        return {
            "valid": False,
            "reason": "No matching courses found for the query.",
        }

    rejections = []
    for code in candidates:
        result = validate_manual_course_add(
            degree_id=degree_id,
            enrollment_year=enrollment_year,
            completed_courses=completed_courses,
            existing_plan_terms=existing_plan_terms,
            target_year=target_year,
            target_term=target_term,
            course_code=code,
        )
        if result.get("valid"):
            result["selected_from_query"] = course_query
            return result
        rejections.append({"course_code": code, "reason": result.get("reason")})

    return {
        "valid": False,
        "reason": (
            "Matching courses were found, but none passed term or duplicate checks "
            "for the selected slot."
        ),
        "checked_candidates": rejections[:10],
    }


def normalize_completed_courses(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    codes = []
    for item in raw:
        code = str(item).strip().upper()
        if code:
            codes.append(code)
    return sorted(set(codes))


def normalize_existing_plan(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []

    plan = []
    for term in raw:
        if not isinstance(term, dict):
            continue
        year = _to_int(term.get("year"), 0)
        label = _normalize_term(str(term.get("term", "")))
        if not year or not label:
            continue

        entries = []
        for entry in term.get("courses", []):
            if isinstance(entry, dict):
                code = str(entry.get("course_code", "")).strip().upper()
                if code:
                    entries.append({"course_code": code})
            else:
                code = str(entry).strip().upper()
                if code:
                    entries.append({"course_code": code})

        plan.append({"year": year, "term": label, "courses": entries})

    return plan
