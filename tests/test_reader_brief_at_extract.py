"""The Reader brief is written at extraction and survives a projection rebuild.

Before: 6,377 single-source events on prod, 46 with a brief; the first reader
of a ticket paid for a live generation (27s measured). And a cached brief was
dropped the moment a second outlet arrived, because the rebuild replaced the
projection wholesale (565 of 1,658 multi-source events had none).
"""

from correlation.consumer import extracted_reader_brief

BRIEF = "The Cabinet raised the EPFO wage ceiling to Rs 25,000. About 51 lakh more workers come under the scheme. The change takes effect next quarter."


def test_the_extractor_brief_maps_to_the_persisted_shape():
    out = extracted_reader_brief({"reader_brief": BRIEF, "watch_points": ["Notification date", "", "Employer response", "Fourth point", "Fifth"]})
    assert out == {"text": BRIEF, "points": ["Notification date", "Employer response", "Fourth point"]}


def test_a_brief_that_is_not_one_is_dropped():
    assert extracted_reader_brief({}) is None
    assert extracted_reader_brief({"reader_brief": "Short."}) is None
    assert extracted_reader_brief({"reader_brief": "One long sentence without a second one that goes on and on and on and on and on and on"}) is None
