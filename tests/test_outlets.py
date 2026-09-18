"""Outlet identity: where a source sits on the coverage bar and what its
monogram says. Facts of the source (country, language), never a rating."""

from api.routes.serialization import outlet_refs
from common.outlets import Outlet, classify, code_for


def test_origin_is_country_and_language_not_a_label():
    assert classify("IN", "en") == "national"
    assert classify("IN", "kn") == "regional"
    assert classify("IN", None) == "national"  # language unknown → the English-national default
    assert classify("GB", "en") == "intl"
    assert classify("QA", "ar") == "intl"
    assert classify("US", "en", "cve_feed") == "wire"


def test_monogram_prefers_the_registry_then_initials():
    assert code_for("thehindu", "The Hindu — Karnataka") == "TH"  # publisher, so state feeds share one
    assert code_for("bbc", "BBC News Hindi") == "BBC"
    assert code_for("unknown_paper", "The Daily Star of Chennai") == "DSC"
    assert code_for("solo", "Prajavani") == "PRA"


def test_outlet_refs_follow_the_bar_order_then_name():
    reg = {
        "prajavani": Outlet("prajavani", "prajavani", "Prajavani", "PV", "regional", "kn", "IN"),
        "bbc_world": Outlet("bbc_world", "bbc", "BBC World", "BBC", "intl", "en", "GB"),
        "thehindu": Outlet("thehindu", "thehindu", "The Hindu", "TH", "national", "en", "IN"),
        "ndtv": Outlet("ndtv", "ndtv", "NDTV", "NDTV", "national", "en", "IN"),
    }
    refs = outlet_refs(["prajavani", "bbc_world", "thehindu", "ndtv", "gone"], reg)
    assert [r.code for r in refs] == ["NDTV", "TH", "BBC", "PV"]
    assert outlet_refs(["thehindu"], None) == []
