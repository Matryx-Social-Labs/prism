"""The two pure pieces of the podcast pipeline: packing segments into windows
and merging matched windows into clips."""
import uuid

from podcasts.match import CLIP_MAX_S, Hit, entity_hits, merge_runs
from podcasts.transcribe import windows_from_segments


def seg(start, end, text="…"):
    return {"start": start, "end": end, "text": text}


def test_windows_pack_thirty_to_sixty_seconds_and_cut_at_a_segment_end():
    segments = [seg(i * 10, i * 10 + 10, f"s{i}") for i in range(10)]  # 100 s in 10 s segments
    words = [{"word": f"w{i}", "start": i * 10 + 1, "end": i * 10 + 2} for i in range(10)]
    wins = windows_from_segments(segments, words)
    assert [(w.start_s, w.end_s) for w in wins] == [(0, 30), (30, 60), (60, 90), (90, 100)]
    assert wins[0].text == "s0 s1 s2"
    assert [w[0] for w in wins[1].words] == ["w3", "w4", "w5"], "each window carries its own words"


def test_a_long_segment_never_makes_a_window_over_the_cap():
    segments = [seg(0, 25, "a"), seg(25, 50, "b"), seg(50, 75, "c")]
    wins = windows_from_segments(segments, [])
    assert all(w.end_s - w.start_s <= 60 for w in wins)
    assert (wins[0].start_s, wins[0].end_s) == (0, 50)


def test_entity_hits_are_whole_words_and_initials_stay_case_sensitive():
    text = "The BJP said Siddaramaiah would meet Modi; a bjp worker disagreed."
    assert entity_hits(text, ["Siddaramaiah", "Narendra Modi", "BJP"]) == 2
    assert entity_hits("the bjp worker", ["BJP"]) == 0, "initials only count as written"
    assert entity_hits("Modinagar is a town", ["Modi"]) == 0, "not a substring"


def _hit(ev, ep, seq, start, score):
    return Hit(ev, uuid.uuid4(), ep, seq, start, start + 40, score, 1)


def test_consecutive_matched_windows_merge_into_one_clip_under_the_cap():
    ev, ep = uuid.uuid4(), uuid.uuid4()
    hits = [_hit(ev, ep, 3, 120, 0.86), _hit(ev, ep, 4, 160, 0.91), _hit(ev, ep, 5, 200, 0.85), _hit(ev, ep, 9, 400, 0.87)]
    clips = merge_runs(hits)
    assert len(clips) == 2, "the run 3-4-5 is one clip; 9 stands alone"
    run = next(c for c in clips if c.seq == 4)
    assert run.end_s - run.start_s <= CLIP_MAX_S
    assert run.start_s == 120 and run.score == 0.91


def test_a_run_longer_than_the_cap_keeps_the_best_window_and_its_neighbours():
    ev, ep = uuid.uuid4(), uuid.uuid4()
    hits = [_hit(ev, ep, i, i * 40, 0.85 + (0.05 if i == 5 else 0)) for i in range(10)]  # 400 s of matches
    (clip,) = merge_runs(hits)
    assert clip.seq == 5 and clip.start_s <= 200 <= clip.end_s
    assert clip.end_s - clip.start_s <= CLIP_MAX_S


def test_title_hits_count_the_headlines_own_words_not_glue():
    from podcasts.match import title_hits, title_words

    assert title_words("US House clears Russia sanctions bill authorizing 100% tariffs on India") == {"house", "clears", "russia", "sanctions", "bill", "authorizing", "tariffs"}
    clip = "the U.S. House is expected to pass a new law which would put up to 100% tariff sanctions on India"
    assert title_hits(clip, "US House clears Russia sanctions bill authorizing 100% tariffs on India") >= 2
    assert title_hits(clip, "BMC issues notices to 294 establishments without Marathi signboards") == 0


def test_a_window_backs_one_event_per_story_the_best_one():
    from podcasts.match import one_event_per_story

    ev1, ev2, ev3, ep, w = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    hits = [Hit(ev1, w, ep, 1, 0, 40, 0.90, 1, "semicon"), Hit(ev2, w, ep, 1, 0, 40, 0.92, 1, "semicon"), Hit(ev3, w, ep, 1, 0, 40, 0.85, 1, "tata")]
    kept = one_event_per_story(hits)
    assert {h.event_id for h in kept} == {ev2, ev3}
