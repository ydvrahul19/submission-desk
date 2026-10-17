import json
from datetime import date
from pathlib import Path

import pytest

from core.extract import extract
from core.fields import normalize
from core.ingest import read_file
from core.models import Doc
from core.pipeline import analyze
from samples.make_samples import build

TODAY = date(2026, 10, 17)


def run(text, client=None, today=TODAY):
    return analyze([Doc("t", [text])], client, today)


def states(res):
    return [r.state for r in res["rules"]]


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    root = tmp_path_factory.mktemp("s")
    build(root, TODAY)
    out = {}
    for d in sorted(root.iterdir()):
        docs = read_file("submission.eml", (d / "submission.eml").read_bytes())
        out[d.name[0]] = docs
    return out


# ---- end to end on real files (eml + pdf + xlsx + docx + csv) ----
def test_sample1_clean_pdf_xlsx(samples):
    r = analyze(samples["1"], None, TODAY)
    assert states(r) == ["pass"] * 5 and r["state"] == "pass"
    assert r["fields"]["tiv"].value == 3_400_000          # came from the xlsx
    assert r["fields"]["year"].candidates[0].source.startswith("application.pdf")


def test_sample2_outside_appetite_docx_csv(samples):
    r = analyze(samples["2"], None, TODAY)
    assert states(r) == ["fail", "fail", "fail", "fail", "pass"] and r["state"] == "fail"
    assert r["fields"]["tiv"].value == 14_000_000          # "$14.0 million" from csv


def test_sample3_conflict_and_missing(samples):
    r = analyze(samples["3"], None, TODAY)
    f = r["fields"]
    assert f["tiv"].status == "conflict" and set(f["tiv"].distinct) == {8_200_000, 12_500_000}
    assert f["loss"].status == "missing"
    assert states(r) == ["needs_info", "pass", "needs_info", "pass", "fail"]
    assert "disagree" in r["email"] and "Losses" in r["email"]
    assert r["state"] == "fail"                            # 6 days lead time


# ---- rule boundaries ----
BASE = "TIV: $10,000,000\nOperations: Cafe\nLosses: 2\nYear built: 1980\nInsured: A\nEffective date: 2026-10-31"


def test_boundaries_all_pass():
    assert states(run(BASE)) == ["pass"] * 5


@pytest.mark.parametrize("old,new,idx", [
    ("$10,000,000", "$10,000,001", 0), ("Losses: 2", "Losses: 3", 2),
    ("Year built: 1980", "Year built: 1979\nSprinklers: no", 3), ("2026-10-31", "2026-10-30", 4)])
def test_one_past_boundary_fails(old, new, idx):
    assert states(run(BASE.replace(old, new)))[idx] == "fail"


def test_old_building_needs_sprinkler_data_then_passes():
    t = BASE.replace("1980", "1970")
    assert states(run(t))[3] == "needs_info"
    assert states(run(t + "\nSprinklers: full"))[3] == "pass"
    assert states(run(t + "\nSprinklers: none"))[3] == "fail"


def test_new_building_does_not_need_sprinklers():
    assert states(run(BASE))[3] == "pass"


def test_empty_submission_never_guesses():
    r = run("hello")
    assert states(r) == ["needs_info"] * 5 and r["state"] == "hold"


def test_same_value_twice_is_not_a_conflict():
    R, _, _ = extract([Doc("a", ["TIV: $5,000,000"]), Doc("b", ["Total insured value: 5000000"])])
    assert R["tiv"].status == "ok"


# ---- normalisation ----
@pytest.mark.parametrize("t,raw,exp", [
    ("money", "$14.0 million", 14_000_000), ("money", "3m", 3_000_000), ("money", "8,200,000", 8_200_000),
    ("int", "none", 0), ("yesno", "partial", "yes"), ("yesno", "None", "no"),
    ("date", "October 31, 2026", "2026-10-31"), ("date", "garbage", None)])
def test_normalize(t, raw, exp):
    assert normalize(t, raw) == exp


# ---- LLM path (mocked): evidence must be real ----
def llm(payload):
    return lambda prompt: "```json\n" + json.dumps({"fields": payload}) + "\n```"


def test_llm_value_with_real_quote_is_used():
    doc = "The building was constructed in 1974 and has no sprinklers."
    c = llm({"year": [{"value": "1974", "quote": "constructed in 1974", "doc": "t"}]})
    r = run(doc, c)
    assert r["fields"]["year"].value == 1974 and r["fields"]["year"].candidates[0].method == "llm"
    assert r["mode"].startswith("LLM")


def test_llm_hallucinated_quote_is_rejected():
    c = llm({"tiv": [{"value": "99000000", "quote": "TIV is ninety nine million", "doc": "t"}]})
    r = run("TIV: $5,000,000", c)
    assert r["fields"]["tiv"].value == 5_000_000           # fell back to rule-based evidence


def test_llm_failure_falls_back():
    def boom(_):
        raise TimeoutError()
    r = run(BASE, boom)
    assert states(r) == ["pass"] * 5 and "failed" in r["warning"]


def test_llm_bad_json_falls_back():
    r = run(BASE, lambda p: "not json")
    assert states(r) == ["pass"] * 5 and r["warning"]


# ---- ingestion robustness ----
def test_corrupt_pdf_does_not_crash():
    d = read_file("bad.pdf", b"not a pdf")[0]
    assert "could not read" in d.text


def test_unknown_extension_read_as_text():
    assert read_file("n.txt", b"Insured: X")[0].text == "Insured: X"


def test_unneeded_missing_field_is_not_chased():
    t = "Insured: Z\nOperations: Cafe\nTIV: $2m\nLosses: 0\nYear built: 2001\nEffective date: 2026-12-01"
    r = run(t)                       # sprinklers never stated, but a 2001 building does not need them
    assert r["state"] == "pass" and "Sprinklers" not in r["email"]


def test_needed_missing_field_is_chased():
    r = run("Insured: Z\nOperations: Cafe\nTIV: $2m\nLosses: 0\nYear built: 1960\nEffective date: 2026-12-01")
    assert r["state"] == "hold" and "Sprinklers" in r["email"]
