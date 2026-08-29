"""Cross-lingual alignment per Indian language, for candidate embedding models.

    uv sync --group bench
    uv run python -m tools.score_crosslingual

WHY THIS AND NOT THE MONOLINGUAL TEST. tools/score_embeddings measures whether
two same-language articles about one event land close. This measures whether a
Kannada article and its English counterpart land close — which is what decides
if multilingual ingestion actually pays for itself. A Hindi and an English report
of one event are two INDEPENDENT sources, and corroboration is the product's
central claim; if the model cannot align them, the non-English half is dead
weight in the story graph no matter how good its monolingual behaviour is.

METHOD: FLORES-200 devtest, 1012 professionally translated parallel sentences per
language. For each language L, embed N English sentences and their N translations,
then ask: does the true translation rank #1 among all N candidates?

  P@1 = fraction where the correct translation is the nearest neighbour.

Chance is 1/N. This needs no story labels, no LLM, and no production data, and it
is the standard bitext-retrieval benchmark — so results are comparable with
published numbers rather than only with each other.

CAVEAT worth stating up front: FLORES is Wikipedia-domain prose, not news
headlines. A model that aligns FLORES may still do worse on short, entity-dense
headlines. Treat a PASS here as necessary, not sufficient — a FAIL is decisive,
a PASS earns a second test on real headlines.
"""

from __future__ import annotations

import argparse
from pathlib import Path

FLORES = Path(".cache/flores/flores200_dataset/devtest")

# Indian languages in FLORES-200, by the product's likely priority.
LANGS = {
    "hindi": "hin_Deva", "tamil": "tam_Taml", "kannada": "kan_Knda",
    "telugu": "tel_Telu", "malayalam": "mal_Mlym", "bengali": "ben_Beng",
    "marathi": "mar_Deva", "gujarati": "guj_Gujr", "punjabi": "pan_Guru",
    "odia": "ory_Orya", "assamese": "asm_Beng", "urdu": "urd_Arab",
}

MODELS = [
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",  # incumbent
    "intfloat/multilingual-e5-base",                                # 768, no migration
    "intfloat/multilingual-e5-large",                               # 1024
    "sentence-transformers/LaBSE",                                  # bitext specialist
    "krutrim-ai-labs/Vyakyarth",                                    # Indic-specific
]


def _read(code: str, n: int) -> list[str]:
    p = FLORES / f"{code}.devtest"
    if not p.exists():
        return []
    return p.read_text(encoding="utf-8").splitlines()[:n]


def _prefix(model: str) -> str:
    # E5 REQUIRES this. Omitting it is a silent quality loss that would be
    # misread as "the model is bad at Indic".
    return "query: " if "e5" in model.lower() else ""


def run(models: list[str], n: int) -> None:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    eng = _read("eng_Latn", n)
    results: dict[str, dict[str, float]] = {}

    for model_name in models:
        try:
            st = SentenceTransformer(model_name, trust_remote_code=True)
        except Exception as exc:  # noqa: BLE001 - a model that will not load is a result
            print(f"\n=== {model_name} ===\n  could not load: {type(exc).__name__}: {exc}")
            continue
        pre = _prefix(model_name)
        e_vec = st.encode([pre + s for s in eng], normalize_embeddings=True,
                          batch_size=32, show_progress_bar=False)
        row: dict[str, float] = {}
        for lang, code in LANGS.items():
            tgt = _read(code, n)
            if len(tgt) != len(eng):
                continue
            t_vec = st.encode([pre + s for s in tgt], normalize_embeddings=True,
                              batch_size=32, show_progress_bar=False)
            sim = np.asarray(e_vec) @ np.asarray(t_vec).T
            row[lang] = float((sim.argmax(axis=1) == np.arange(len(eng))).mean())
        results[model_name] = row
        print(f"\n=== {model_name} ===")
        for lang, p1 in sorted(row.items(), key=lambda kv: -kv[1]):
            bar = "#" * int(p1 * 40)
            print(f"  {lang:11} P@1 {p1:6.3f}  {bar}")

    if len(results) > 1:
        print(f"\n=== summary: P@1 by language (n={n}, chance={1/n:.4f}) ===")
        names = list(results)
        print(f"  {'language':11} " + " ".join(f"{m.split('/')[-1][:22]:>22}" for m in names))
        for lang in LANGS:
            cells = " ".join(f"{results[m].get(lang, float('nan')):>22.3f}" for m in names)
            print(f"  {lang:11} {cells}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=300, help="parallel sentences per language")
    ap.add_argument("--models", default=",".join(MODELS))
    a = ap.parse_args()
    if not FLORES.exists():
        raise SystemExit(f"FLORES not found at {FLORES}")
    run([m.strip() for m in a.models.split(",")], a.n)


if __name__ == "__main__":
    main()
