"""Every cosine distance in the correlation layer must move with the model.

Distances are not comparable across embedding models, and the failure is silent
in both directions: too tight and the match tier stops firing (recall collapses
and the model gets blamed), too loose and the graph goes dense and stories merge.

Three constants were scaled and four were not. The four survived a model swap as
raw mpnet numbers, and the worst of them —
partition.STORY_EMBED_EDGE_MAX_DIST — was added with the v2 story layer AFTER
tools/tune_embed_threshold was written, so it was not even on that tool's list of
what a swap invalidates. That is the gap this file closes.
"""

import re
from pathlib import Path

import pytest

import correlation.clustering as clustering

MPNET = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
E5 = "intfloat/multilingual-e5-base"

# name -> (module path, attribute)
SCALED = {
    "EMBEDDING_DISTANCE_THRESHOLD": ("correlation/clustering.py", "embedding"),
    "ENTITY_MATCH_NEAR_DISTANCE": ("correlation/clustering.py", "entity_near"),
    "ENTITY_MATCH_LOOSE_DISTANCE": ("correlation/clustering.py", "entity_loose"),
    "EMBED_FAR": ("correlation/threads.py", "embed_far"),
    "STORY_MAX_EMBED_DIST": ("correlation/threads.py", "story_max"),
    "STORY_EMBED_EDGE_MAX_DIST": ("correlation/partition.py", "story_edge_max"),
}


def test_every_model_defines_every_key():
    """A model missing a key would fall back to the incumbent's number for that
    one constant only — a half-swapped scale, which is worse than either."""
    keys = {k for v in clustering._SCALE.values() for k in v}
    for model, scale in clustering._SCALE.items():
        assert set(scale) == keys, f"{model} is missing {keys - set(scale)}"


def test_the_two_models_disagree_about_every_distance():
    """If a constant were the same for both, it would mean it had not actually
    been recalibrated — which is exactly how the four unscaled ones looked."""
    mp, e5 = clustering._SCALE[MPNET], clustering._SCALE[E5]
    for key in mp:
        assert e5[key] < mp[key], f"{key}: E5 compresses the space, so it must be tighter"


def test_e5_distances_sit_inside_its_measured_range():
    """mE5's same-event median is 0.063 and its different-event median 0.145
    (tools/tune_embed_threshold). A threshold outside that band is not a
    threshold — above it everything matches, below it nothing does."""
    e5 = clustering._SCALE[E5]
    assert e5["embedding"] <= 0.063, "the near-dup tier must be tighter than the same-event median"
    for key, v in e5.items():
        assert 0.0 < v < 0.35, f"{key}={v} is outside anything mE5's distribution can mean"


@pytest.mark.parametrize("const,where", [(k, v[0]) for k, v in SCALED.items()])
def test_no_distance_constant_is_a_bare_literal(const, where):
    """The regression itself. Each of these must be assigned from _scale(), not
    typed as a number — a literal is how all four of them drifted."""
    line = next(
        ln for ln in Path(where).read_text().splitlines()
        if re.match(rf"^{const}\s*=", ln)
    )
    assert "_scale()" in line, f"{const} in {where} is a hardcoded distance: {line.strip()}"
