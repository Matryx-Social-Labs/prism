from common.images import hi_res


def test_bbc_and_assettype_thumbnails_are_asked_for_at_tile_width():
    assert hi_res("https://ichef.bbci.co.uk/ace/ws/240/cpsprodpb/fa82/live/9460-b446.png") == "https://ichef.bbci.co.uk/ace/ws/800/cpsprodpb/fa82/live/9460-b446.png.webp"
    assert hi_res("https://cf-images.assettype.com/prajavani/2026-09-19/x/a.avif?w=280") == "https://cf-images.assettype.com/prajavani/2026-09-19/x/a.avif?w=800"
    assert hi_res("https://staticimg.amarujala.com/assets/images/2026/09/17/a.jpeg?w=") == "https://staticimg.amarujala.com/assets/images/2026/09/17/a.jpeg?w=", "an empty w= already serves the master"
    assert hi_res("https://cf-images.assettype.com/p/a.avif?w=1200") == "https://cf-images.assettype.com/p/a.avif?w=1200", "never shrink"


def test_other_publishers_urls_are_left_exactly_alone():
    for u in ["https://th-i.thgim.com/public/incoming/x/article7.ece/alternates/LANDSCAPE_1200/a.jpg", "https://static.toiimg.com/photo/msid-134351581,imgsize-43258.cms", None, ""]:
        assert hi_res(u) == u
