# Submission Desk

A small application that reads a fictional insurance broker email and its attachments, extracts key facts **with the
exact line of evidence they came from**, evaluates five underwriting rules, and produces an **underwriter summary** and a
**draft follow-up email** to the broker.

Built for the first-round practical project (AI Solutions Developer, Knight Management Insurance Services).

> **Status note:** the five rules and the seven fields in this version are placeholders I defined while building the
> engine. They live in two small files (`core/rules.py`, `core/fields.py`) and are designed to be swapped for the
> assignment's rules and field specification. See "Extending".

## Contents
1. [What it does](#what-it-does) · 2. [Quick start](#quick-start) · 3. [How it works](#how-it-works) · 4. [Fields and rules](#fields-and-rules)
5. [Missing and conflicting information](#missing-and-conflicting-information) · 6. [LLM modes](#llm-modes) · 7. [Samples](#samples)
8. [Tests](#tests) · 9. [Project structure](#project-structure) · 10. [Extending](#extending) · 11. [Design decisions](#design-decisions)
12. [Limitations](#limitations) · 13. [Troubleshooting](#troubleshooting) · 14. [AI tools, time spent](#ai-tools-and-time-spent)

## What it does
- Reads **.eml** (email plus its attachments), **PDF**, **DOCX**, **XLSX**, **CSV** and **TXT**, or pasted email text.
- Extracts 7 fields. Every value shows the **source file (and page)** and the **verbatim line** it came from.
- Evaluates 5 rules. Each returns **Pass**, **Fail** or **Needs info**.
- Never guesses: missing or conflicting data becomes "Needs info" and is asked about in the draft email.
- Gives one overall verdict: *Ready to quote*, *Hold for information*, or *Outside appetite*.
- Works with no LLM (rule-based), a **local Ollama model**, or the **Claude API**.

## Quick start
Requires Python 3.10+ (3.12 is the safest choice on Windows).

**Mac / Linux**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
**Windows PowerShell**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Then (all systems):
```bash
python samples/make_samples.py     # create the 3 fictional sample submissions
python -m pytest -q                # expect: 28 passed
streamlit run app.py               # opens http://localhost:8501
```
In the sidebar choose a sample (or upload files / paste text) and click **Analyze submission**. If you upload or paste your
own data, set **Sample** to `(none)`; otherwise the sample and your data are analysed together.

## How it works
```
files / pasted text
      |  core/ingest.py      PDF, DOCX, XLSX, CSV, EML -> Doc(name, pages)
      v
 extraction  core/extract.py + core/llm.py
      |   1. LLM (optional) proposes value + verbatim quote + document
      |   2. code VERIFIES the quote exists in that document, else discards it
      |   3. rule-based (regex) extraction fills anything the LLM could not evidence
      v
 per-field result: ok | missing | conflict, with every candidate and its evidence
      |  core/rules.py       5 deterministic rules -> pass | fail | needs_info
      v
 core/report.py   verdict + underwriter summary + follow-up email
      v
 app.py (Streamlit UI)
```
`core/pipeline.py` wires these steps into one function, `analyze(docs, client, today)`. `today` can be passed in, which
keeps the date rule testable.

## Fields and rules
| Field | Example evidence |
|---|---|
| Insured | `Named insured: Harbor Bakes LLC` |
| Operations | `Operations: Retail bakery and cafe` |
| Total insured value | `Total insured value: $3,400,000` (also `TIV: $14.0 million`, `$3m`) |
| Year built | `Year built: 2008` |
| Sprinklers | `Sprinklers: yes / full / partial / no / none` |
| Losses, last 5 years | `Losses in last 5 years: 1` (also `Claims ...: none`) |
| Effective date | `Effective date: 2026-11-21` (also `December 20, 2026`) |

| Rule | Passes when | Needs info when |
|---|---|---|
| R1 | Total insured value <= $10,000,000 | value missing or conflicting |
| R2 | Operations do not match a prohibited class (fireworks, explosives, cannabis, asbestos) | operations missing or conflicting |
| R3 | At most 2 losses in 5 years | losses missing or conflicting |
| R4 | Built 1980 or later, **or** sprinklered | year missing or conflicting; or building is older than 1980 and sprinkler data is missing |
| R5 | Effective date at least 14 days from today | date missing or conflicting |

Thresholds are constants at the top of `core/rules.py`. R4 only asks about sprinklers when the building is old, so the app
does not chase information it does not need.

## Missing and conflicting information
- **Missing:** the field is not stated anywhere. Rules that need it return *Needs info*; the email asks for it.
- **Conflict:** documents give different values for the same field (e.g. $8.2M in the email, $12.5M in the spreadsheet).
  The app shows both values with their sources, does not pick one, and the email asks which is correct.
- The same value repeated in several documents is **not** a conflict.
- A missing field is only requested if a rule actually needed it. Conflicts are always raised.
- Failed rules are reported in the underwriter summary, not in the broker email.

## LLM modes
Copy `.env.example` to `.env` (never commit `.env`).

| `LLM_PROVIDER` | Behaviour |
|---|---|
| `none` (default) | Rule-based extraction only. No network, no key. |
| `ollama` | Local model. Install Ollama, `ollama pull llama3.2`, set `OLLAMA_MODEL` if different. Free. |
| `anthropic` | Claude API. Set `ANTHROPIC_API_KEY` and optionally `ANTHROPIC_MODEL`. |

**Safety of the LLM step:** the model must return a verbatim quote for every value. The code checks that the quote appears in the
named document (ignoring whitespace and case). Values with missing or invented quotes are dropped. If the LLM times out,
returns invalid JSON, or fails, the app shows a warning and uses rule-based extraction. Rules never call the LLM.

## Samples
`python samples/make_samples.py` writes three fictional `.eml` submissions into `samples/`. Effective dates are relative to the
day you run it, so re-run it on a new day.

| Sample | Files | Expected result |
|---|---|---|
| 1 Harbor Bakes (clean) | email + PDF + XLSX | Ready to quote, all 5 pass |
| 2 Redline Pyrotech (outside appetite) | email + DOCX + CSV | Outside appetite; R1 to R4 fail, R5 passes |
| 3 Meridian Cold Storage (messy) | email + PDF (2 pages) + XLSX | Insured value conflict ($8.2M vs $12.5M), no loss history, start date 6 days away; email asks for both |

## Tests
`python -m pytest -q` runs 28 tests in `tests/test_kims.py`:
- the three samples end to end through real PDF, DOCX, XLSX, CSV and .eml files;
- every rule at its boundary and one step past it (e.g. $10,000,000 passes, $10,000,001 fails; 14 days passes, 13 fails);
- missing data, conflicting data, repeated identical values, empty input;
- R4 behaviour: new building needs no sprinkler data; old building asks for it, then passes or fails;
- only genuinely needed missing fields are requested;
- value normalisation (`$14.0 million`, `3m`, `none`, written dates);
- mocked LLM: real quote accepted, invented quote rejected, timeout and invalid JSON fall back safely;
- corrupt PDF does not crash ingestion.

The Ollama client code was also exercised against a fake local HTTP server. The Anthropic client has not been run against the real API.

## Project structure
```
app.py                  Streamlit UI
core/ingest.py          files -> text (PDF, DOCX, XLSX, CSV, EML)
core/fields.py          field specification and value normalisation
core/llm.py             optional LLM client and evidence verification
core/extract.py         rule-based extraction, merging, conflict detection
core/rules.py           the five rules (placeholders)
core/report.py          verdict, summary, follow-up email
core/pipeline.py        analyze() entry point
samples/make_samples.py generates the sample submissions
tests/test_kims.py      automated tests
docs/VIDEO_SCRIPT.md    demo video script
.env.example            configuration template (no secrets)
```

## Extending
- **Change or add a rule:** edit `core/rules.py`. Use `add(id, name, [field_keys], fn)`; missing or conflicting inputs are handled for you.
- **Add a field:** add a `Field(...)` to `core/fields.py` (key, label, type, regex, hint for the LLM).
- **Add a file type:** add a reader in `core/ingest.py` and a case in `read_file`.
- **Add a test:** use `run(text, today=...)` helpers in `tests/test_kims.py`.

## Design decisions
- **LLM proposes, code verifies.** Evidence must exist in the source, which prevents hallucinated support.
- **Rules are plain code**, so they are deterministic, explainable and unit-testable.
- **Fail safe, not silent.** Unknown data yields "Needs info"; the draft email asks only for what is needed.
- **Works offline.** The rule-based path needs no key or network, so the demo cannot break on connectivity.
- **One place per concern.** Fields, rules and thresholds are each in one file.
- **Trade-off:** regex extraction is simple and predictable but only understands "label: value" lines; the LLM covers free-text wording.

## Limitations
- The five rules and seven fields are placeholders, not the assignment's official ones.
- Rule-based extraction needs "label: value" lines; free-text wording needs the LLM mode.
- Scanned or image-only PDFs are not OCR'd (the app reports that no text was found).
- Spreadsheets are flattened to "first cell: other cells" rows, so unusual layouts may be missed.
- The effective-date rule compares with today's date.
- The live Claude API path and a real Ollama model have not been run end to end here (client code tested with a fake server and mocks).
- No authentication, storage or live mailbox, as the brief places AWS deployment and mailbox access out of scope.
- The Submission_Template.txt answers and the demo video are separate deliverables not contained in this repository.

## Troubleshooting
- **`source` not recognised on Windows:** use `.venv\Scripts\Activate.ps1`. If scripts are blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **`pip install` fails on a very new Python (3.14):** install Python 3.12 and create the venv with `py -3.12 -m venv .venv`.
- **Sample 1 fails the date rule:** the sample dates are stale; run `python samples/make_samples.py` again.
- **Results look unchanged after uploading:** set **Sample** to `(none)`.
- **Port busy:** `streamlit run app.py --server.port 8502`.

## AI tools and time spent
- **AI tools:** Claude (Anthropic) was used as the AI coding assistant to generate the initial code, tests and this README. I reviewed, ran and tested the code. At run time the app can optionally use Claude (API) or a local Ollama model.
- **Time spent:** [fill in your actual hours here]
