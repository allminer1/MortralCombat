"""Write docs/CLINICAL_REVIEW.md: every piece of interface text in English, Russian and
Kazakh side by side, with a column for the reviewer's correction, followed by the
model-behaviour tables.

    make review-packet          (= python3 tools/review_packet.py --word; standard library only)

With --word it also writes docs/out/CLINICAL_REVIEW.docx (and .html) for a reviewer who
works in Word or on paper. The Word file is made with macOS `textutil`; on other systems
only the HTML is written, which Word opens as well. docs/out/ is not committed.

The texts are read from frontend/src/i18n/*.json, so the packet always shows what the
site would display. Nothing here changes the site: corrections come back on paper or in
the document and are then entered into the JSON files.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
I18N = REPO / "frontend" / "src" / "i18n"
BEHAVIOUR = REPO / "docs" / "MODEL_BEHAVIOUR.md"
OUT = REPO / "docs" / "CLINICAL_REVIEW.md"
WORD_DIR = REPO / "docs" / "out"
LANGS = (("en", "English"), ("ru", "Russian"), ("kk", "Kazakh (draft)"))

# (title, where the reader sees it, top-level keys or dotted keys). Review order: what a
# clinician reads on the calculator first, interface-only text last.
SECTIONS = [
    (
        "1. Calculator form",
        "Titles and help above the two groups of inputs, the label of each of the 11 inputs, units, and the "
        "answers offered.",
        ["groups", "fields", "units", "choices"],
    ),
    (
        "2. Result",
        "Shown after a calculation: headings, the sentence under the curve, the details list, the warning for "
        "birth weight above 1,500 g, and the limitations box that is always shown with a result.",
        ["result", "warnings", "limitations"],
    ),
    (
        "3. Printed report",
        "The one-page report (`/report`). It also repeats the input labels, the limitations and the "
        "intended-use line from the other sections.",
        ["report", "footer.intendedUse"],
    ),
    (
        "4. About page",
        "`/about`. The numbers on that page (cohort sizes, C-index and so on) are not in this table: they are "
        "taken from the model card and were checked against the article.",
        ["about"],
    ),
    (
        "5. Saving and history — NOT on the live site",
        "Only visible when accounts are switched on, which they are not. Review together with the decision "
        "to enable accounts. The case-code warning is the important text here.",
        ["save", "history"],
    ),
    (
        "6. Other interface text (language check only)",
        "Buttons, navigation, input-error messages, sign-in. No clinical content; listed so that the Russian "
        "and Kazakh can be checked by a native speaker.",
        ["app", "nav", "form", "errors", "auth", "footer"],
    ),
]

QUESTIONS = [
    "**Bad obstetric history.** The form has no explanation of what counts. Is a one-line definition wanted "
    "next to the field, and what should it say? (Today: no explanation.)",
    '**Order and grouping of the inputs.** Is "At birth / NICU admission" and "Confirmed diagnoses" the '
    "right split, and is respiratory failure grade in the right group?",
    '**Heart rate and SpO₂.** The help says "single values taken right after birth, at NICU admission". Is '
    "that how they were recorded in the study?",
    "**Day 56.** The curve is drawn fainter from day 56 with the sentence about few infants still under "
    "observation. Is day 56 the right point, and is the sentence right?",
    "**Rounding.** The headline shows whole percent (65 %), the details one decimal (65.2 %). Acceptable?",
    "**Limitations box.** Are the four sentences correct and sufficient? Anything that must be added?",
    '**Intended-use line** in the footer and on the report: is "For research use. Not a substitute for '
    'clinical judgement." the right statement for this tool?',
    "**Input ranges.** The form accepts birth weight 400–2000 g, gestational age 20–42 weeks, Apgar 0–10, "
    "heart rate 60–200, SpO₂ 40–100 (the limits of the old calculator), and warns only above 1,500 g. Part B "
    "shows what the model returns at the edges of these ranges. Should the accepted ranges be narrower, or "
    "should more warnings be shown?",
    "**Kazakh.** The whole Kazakh column was drafted by an AI system that is not a native speaker. The clinical "
    "terms and abbreviations listed in Part A, section 7 need a clinician who works in Kazakh.",
]


def load(lang: str) -> dict:
    return json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))


def flatten(node, prefix: str = "") -> dict[str, str]:
    if isinstance(node, dict):
        out: dict[str, str] = {}
        for key, value in node.items():
            out |= flatten(value, f"{prefix}.{key}" if prefix else key)
        return out
    return {prefix: str(node)}


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def inline(text: str) -> str:
    text = html.escape(text.replace("\\|", "\x00"), quote=False).replace("\x00", "|")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", text)


def to_html(markdown: str) -> str:
    """HTML for exactly the Markdown this script writes: headings, paragraphs, lists, tables."""
    out, mode = [], None  # mode: None | "ul" | "ol" | "table" | "p"

    def close() -> None:
        nonlocal mode
        if mode:
            out.append({"ul": "</ul>", "ol": "</ol>", "table": "</table>", "p": "</p>"}[mode])
        mode = None

    for line in markdown.splitlines():
        if line.startswith("<!--") or line.strip().endswith("-->"):
            continue
        if not line.strip():
            close()
        elif line.startswith("#"):
            close()
            level = len(line) - len(line.lstrip("#"))
            out.append(f"<h{level}>{inline(line[level:].strip())}</h{level}>")
        elif line.startswith("|"):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
            if all(re.fullmatch(r":?-+:?", c) for c in cells):
                continue
            tag = "td" if mode == "table" else "th"
            if mode != "table":
                close()
                out.append("<table>")
                mode = "table"
            out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
        elif re.match(r"(- |\d+\. |\\?\* )", line):
            kind = "ol" if line[0].isdigit() else "ul"
            if line.startswith("\\*"):  # footnote line of the behaviour report
                close()
                out.append(f"<p>{inline(line[1:])}</p>")
                continue
            if mode != kind:
                close()
                out.append(f"<{kind}>")
                mode = kind
            out.append(f"<li>{inline(re.sub(r'^(- |\d+\. )', '', line))}")
        elif line.startswith("  ") and mode in ("ul", "ol"):
            out.append(" " + inline(line.strip()))
        else:
            if mode != "p":
                close()
                out.append("<p>")
                mode = "p"
            out.append(inline(line) + " ")
    close()
    style = (
        "@page{size:A4 landscape;margin:15mm} body{font-family:Arial,sans-serif;font-size:10pt}"
        "table{border-collapse:collapse;width:100%;margin:6pt 0 12pt}"
        "th,td{border:1px solid #777;padding:3pt 5pt;vertical-align:top;text-align:left}"
        "th{background:#e8eef0} code{font-size:8.5pt} h1{font-size:16pt} h2{font-size:13pt} h3{font-size:11pt}"
    )
    title = "NeoMortalSurv - text for clinical review"
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{style}</style></head>"
        "<body>" + "\n".join(out) + "</body></html>"
    )


def write_word(markdown: str) -> None:
    WORD_DIR.mkdir(exist_ok=True)
    page = WORD_DIR / "CLINICAL_REVIEW.html"
    page.write_text(to_html(markdown), encoding="utf-8")
    print(f"wrote {page.relative_to(REPO)}")
    if shutil.which("textutil"):
        target = WORD_DIR / "CLINICAL_REVIEW.docx"
        subprocess.run(["textutil", "-convert", "docx", "-output", str(target), str(page)], check=True)
        print(f"wrote {target.relative_to(REPO)}")
    else:
        print("textutil not found: open the .html file in Word and save it as .docx")


def main() -> int:
    texts = {
        lang: flatten({k: v for k, v in load(lang).items() if not k.startswith("_")}) for lang, _ in LANGS
    }
    keys = list(texts["en"])
    for lang, _ in LANGS:
        if list(texts[lang]) != keys and set(texts[lang]) != set(keys):
            raise SystemExit(f"{lang}.json does not have the same keys as en.json")

    used: set[str] = set()
    lines = [
        "# NeoMortalSurv — text for clinical review",
        "",
        "<!-- Generated by tools/review_packet.py (make review-packet). Do not edit by hand: corrections",
        "     go into frontend/src/i18n/*.json, then regenerate. -->",
        "",
        "**Status: every text below is a draft (`TODO(clinical-review)`).** The English and Russian columns",
        "are what https://neomortalsurv.net shows today. None of it has been checked by a clinician. The",
        "Kazakh column is not shown on the site.",
        "",
        "## How to review",
        "",
        "- Read the English and Russian of each row as a clinician would read it on the ward.",
        "- Write the corrected text in the last column, or a tick if the row is fine. Mark anything that",
        "  is wrong, unclear, or could be misread at the bedside.",
        "- Words in double braces, such as `{{day}}` or `{{min}}`, are filled in by the program (a day",
        "  number, a limit). Keep them as they are.",
        "- Russian input labels were carried over from the previous calculator; all other Russian text is",
        "  new.",
        "- Part B shows how the model itself behaves. It is not text to correct, but please read it: it",
        "  is the background for question 8 below.",
        "",
        "Reviewer: ____________________   Date: ____________   Languages reviewed: ____________",
        "",
        "## Questions for the reviewer",
        "",
        *[f"{i}. {q}" for i, q in enumerate(QUESTIONS, start=1)],
        "",
        "# Part A — interface text",
        "",
    ]

    for title, where, groups in SECTIONS:
        rows = [k for k in keys if k not in used and any(k == g or k.startswith(g + ".") for g in groups)]
        used.update(rows)
        lines += [f"## {title}", "", where, ""]
        lines += [
            "| Where (key) | " + " | ".join(name for _, name in LANGS) + " | Correction |",
            "|---|---|---|---|---|",
        ]
        for key in rows:
            lines.append(f"| `{key}` | " + " | ".join(cell(texts[lang][key]) for lang, _ in LANGS) + " | |")
        lines.append("")

    missing = [k for k in keys if k not in used]
    if missing:
        raise SystemExit(f"keys not assigned to a section: {missing}")

    terms = load("kk").get("_clinical_terms", {})
    lines += [
        "## 7. Kazakh clinical terms to confirm first",
        "",
        "The terms the Kazakh draft depends on. If one of these is wrong, it is wrong everywhere it is used.",
        "",
        "| Term | Kazakh used in the draft | Correction |",
        "|---|---|---|",
        *[f"| {cell(k.removeprefix('TODO(clinical-review) '))} | {cell(v)} | |" for k, v in terms.items()],
        "",
        "# Part B — how the model behaves",
        "",
        "The model is frozen and is not changed by this review. The tables show what it returns when one",
        "input is varied and the others are held fixed. Some combinations are far from any infant in the",
        "study, and the model still returns a confident number for them.",
        "",
    ]
    behaviour = BEHAVIOUR.read_text(encoding="utf-8").splitlines()
    body = [line for line in behaviour if not line.startswith("<!--")]
    # Demote the report's headings by one level so they sit under Part B.
    lines += [("#" + line if line.startswith("#") else line) for line in body[1:]]

    markdown = "\n".join(lines).rstrip() + "\n"
    OUT.write_text(markdown, encoding="utf-8")
    print(
        f"wrote {OUT.relative_to(REPO)}: {len(keys)} texts in {len(LANGS)} languages, {len(terms)} Kazakh terms"
    )
    if "--word" in sys.argv[1:]:
        write_word(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
