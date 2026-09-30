"""tools/gold_attaches: the human check on the verifier is scored honestly."""

import csv
import json

from tools import gold_attaches


def _sheet(path, answers):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=gold_attaches.COLUMNS)
        w.writeheader()
        for i, (pair, a) in enumerate(answers.items(), 1):
            w.writerow({"n": i, "pair": pair, "answer": a})


def test_scoring_counts_only_agreed_answers_and_reads_every_floor(tmp_path, capsys):
    key = {"population": {"entity_overlap|same": 10, "entity_overlap|different": 10},
           "pairs": {"p1": {"tier": "entity_overlap", "same": 0.95, "follows": 0.1},
                     "p2": {"tier": "entity_overlap", "same": 0.9, "follows": 0.2},
                     "p3": {"tier": "entity_overlap", "same": 0.1, "follows": 0.9},
                     "p4": {"tier": "entity_overlap", "same": 0.05, "follows": 0.1}}}
    (tmp_path / "k.json").write_text(json.dumps(key))
    _sheet(tmp_path / "a.csv", {"p1": "Same", "p2": "s", "p3": "follow-up", "p4": "different"})
    _sheet(tmp_path / "b.csv", {"p1": "same", "p2": "d", "p3": "f", "p4": "unsure"})
    gold_attaches.score([tmp_path / "a.csv", tmp_path / "b.csv"], tmp_path / "k.json")
    out = capsys.readouterr().out
    assert "3 pairs with one agreed answer" in out, "p2 is disputed; p4's unsure leaves the one definite answer"
    assert "verifier at 0.85: attaches 1, precision 1.0, recall 1.0" in out
    assert "follow-up links at 0.85: 1 written, 1 labelled follow-up" in out


def test_kappa_is_one_on_perfect_agreement_and_undefined_on_a_constant():
    assert gold_attaches.kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert gold_attaches.kappa(["a", "a"], ["a", "a"]) is None


def test_a_pushed_task_shows_the_sheets_text_and_hides_the_machines_answer():
    row = {"pair": "p1", "record_headline": "R", "record_summary": "RS", "record_first_reported": "2026-09-21 10:00",
           "article_outlet": "sakshi", "article_published": "2026-09-27 08:00", "article_language": "te",
           "article_title_as_printed": "T", "article_headline_english": "H", "article_summary_english": "S"}
    key = {"pairs": {"p1": {"tier": "entity_overlap", "same": 0.1, "follows": 0.93}}}
    payload = gold_attaches._task_payload(row, key)
    assert payload["kind"] == "attach_identity"
    assert payload["record"]["headline"] == "R" and payload["article"]["title"] == "T"
    assert {k for k in payload if k.startswith("_")} == {"_pair", "_tier", "_same", "_follows"}
