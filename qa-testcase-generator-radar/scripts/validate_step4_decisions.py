"""Validate Step 4 decision coverage before showing clarification questions.

This is a structural gate, not a substitute for semantic review of the PRD.
It prevents a short radar question list from silently replacing the larger
requirement/prototype/context candidate set.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


OPEN_QUESTION = re.compile(r"^\|\s*(Q\d+)\s*\|", re.IGNORECASE)


def extract_open_prd_questions(markdown: str) -> set[str]:
    """Return open Q-numbers from the PRD's 待确认问题 table, if present."""
    in_section = False
    result: set[str] = set()
    for raw in markdown.splitlines():
        line = raw.strip()
        if re.match(r"^#{2,6}\s+.*待确认问题", line):
            in_section = True
            continue
        if in_section and re.match(r"^#{1,6}\s+", line):
            break
        if not in_section:
            continue
        match = OPEN_QUESTION.match(line)
        if not match:
            continue
        cells = [part.strip() for part in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        question, status = cells[1], cells[3]
        if "~~" in question or "已确认" in status or "本期已按" in status:
            continue
        result.add(match.group(1).upper())
    return result


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def count_html_images(source: str) -> int:
    """Count embedded or linked HTML images in the original source, not extracted text."""
    return len(re.findall(r"<img\b", source, flags=re.IGNORECASE))


def validate(prd_markdown: str, audit: dict[str, Any], html_source: str | None = None) -> list[str]:
    errors: list[str] = []
    candidates = audit.get("source_candidates")
    dispositions = audit.get("dispositions")
    questions = audit.get("questions")
    if not isinstance(candidates, list) or not isinstance(dispositions, list) or not isinstance(questions, list):
        return ["source_candidates, dispositions and questions must be arrays"]

    candidate_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(candidates):
        if not isinstance(item, dict) or not _nonempty(item.get("id")):
            errors.append(f"source_candidates[{index}] needs an id")
            continue
        cid = item["id"]
        if cid in candidate_by_id:
            errors.append(f"duplicate candidate id: {cid}")
        candidate_by_id[cid] = item
        if not _nonempty(item.get("source_ref")) or not _nonempty(item.get("topic")):
            errors.append(f"candidate {cid} needs source_ref and topic")

    for qid in sorted(extract_open_prd_questions(prd_markdown)):
        if f"PRD-{qid}" not in candidate_by_id:
            errors.append(f"open PRD question omitted: {qid}")

    question_by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(questions):
        if not isinstance(item, dict) or not _nonempty(item.get("id")):
            errors.append(f"questions[{index}] needs an id")
            continue
        qid = item["id"]
        if qid in question_by_id:
            errors.append(f"duplicate question id: {qid}")
        question_by_id[qid] = item
        for field in ("text", "recommended_answer", "impact", "basis"):
            if not _nonempty(item.get(field)):
                errors.append(f"question {qid} needs {field}")
    if len(questions) > 10:
        errors.append("more than 10 questions; merge by product decision")

    covered: dict[str, int] = {}
    used_questions: set[str] = set()
    allowed = {"ask", "settled", "execution_data", "out_of_scope"}
    for index, item in enumerate(dispositions):
        if not isinstance(item, dict):
            errors.append(f"dispositions[{index}] must be an object")
            continue
        ids = item.get("candidate_ids")
        status = item.get("status")
        if not isinstance(ids, list) or not ids or any(not _nonempty(x) for x in ids):
            errors.append(f"dispositions[{index}] needs candidate_ids")
            continue
        if status not in allowed:
            errors.append(f"dispositions[{index}] has invalid status: {status}")
        if not _nonempty(item.get("reason")):
            errors.append(f"dispositions[{index}] needs reason")
        for cid in ids:
            covered[cid] = covered.get(cid, 0) + 1
            if cid not in candidate_by_id:
                errors.append(f"disposition references unknown candidate: {cid}")
        if status == "ask":
            qid = item.get("question_id")
            if not _nonempty(qid) or qid not in question_by_id:
                errors.append(f"dispositions[{index}] ask needs a displayed question")
            else:
                used_questions.add(qid)
        elif item.get("question_id"):
            errors.append(f"dispositions[{index}] non-ask cannot bind a question")
        if status == "settled" and not _nonempty(item.get("current_source_basis")):
            errors.append(f"dispositions[{index}] settled needs current_source_basis")
        if status == "execution_data" and not _nonempty(item.get("execution_prerequisite")):
            errors.append(f"dispositions[{index}] execution_data needs execution_prerequisite")

    for cid in candidate_by_id:
        if covered.get(cid, 0) == 0:
            errors.append(f"unaccounted candidate: {cid}")
        elif covered[cid] > 1:
            errors.append(f"candidate accounted multiple times: {cid}")
    for qid in question_by_id:
        if qid not in used_questions:
            errors.append(f"displayed question has no candidate: {qid}")

    provenance = audit.get("candidate_source_review")
    if not isinstance(provenance, dict):
        errors.append("candidate_source_review must record independent source checks")
    else:
        for family in ("requirement", "prototype", "knowledge", "radar", "prior_run"):
            entry = provenance.get(family)
            if not isinstance(entry, dict) or entry.get("status") not in {"checked", "not_available", "not_applicable"}:
                errors.append(f"candidate_source_review.{family} needs status")
            elif not _nonempty(entry.get("reason")):
                errors.append(f"candidate_source_review.{family} needs reason")

        image_count = count_html_images(html_source) if html_source is not None else 0
        if image_count:
            prototype = provenance.get("prototype")
            reviews = prototype.get("image_reviews") if isinstance(prototype, dict) else None
            if not isinstance(reviews, list):
                errors.append(f"HTML has {image_count} images; prototype.image_reviews must account for each image")
            else:
                seen: set[int] = set()
                for index, review in enumerate(reviews):
                    if not isinstance(review, dict):
                        errors.append(f"prototype.image_reviews[{index}] must be an object")
                        continue
                    number = review.get("index")
                    if not isinstance(number, int) or isinstance(number, bool) or number < 1 or number > image_count:
                        errors.append(f"prototype.image_reviews[{index}] has invalid image index")
                        continue
                    if number in seen:
                        errors.append(f"prototype image {number} reviewed multiple times")
                    seen.add(number)
                    kind = review.get("kind")
                    if kind not in {"rule", "reference_only"} or not _nonempty(review.get("reason")):
                        errors.append(f"prototype image {number} needs kind and reason")
                    if kind == "rule":
                        ids = review.get("candidate_ids")
                        if not isinstance(ids, list) or not ids or any(cid not in candidate_by_id for cid in ids):
                            errors.append(f"prototype image {number} rule needs known candidate_ids")
                if seen != set(range(1, image_count + 1)):
                    errors.append(f"HTML image inventory incomplete: {len(seen)}/{image_count} reviewed")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prd", type=Path)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--source-html", type=Path, help="Original HTML for embedded-image coverage")
    args = parser.parse_args()
    try:
        prd = args.prd.read_text(encoding="utf-8")
        audit = json.loads(args.audit.read_text(encoding="utf-8"))
        html_source = args.source_html.read_text(encoding="utf-8") if args.source_html else None
        errors = validate(prd, audit, html_source)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"[INVALID] {exc}")
        return 2
    if errors:
        for error in errors:
            print(f"[INVALID] {error}")
        return 1
    print(f"[OK] Step 4: {len(audit['source_candidates'])} candidates, {len(audit['questions'])} questions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
