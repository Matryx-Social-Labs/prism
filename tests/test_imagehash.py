"""Two uploads of one photograph read as one picture; two photographs do not."""
import io

from PIL import Image

from common.imagehash import dhash_bytes, hamming


def _png(draw) -> bytes:
    im = Image.new("L", (64, 48), 255)
    draw(im)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _jpeg(im_bytes: bytes, quality: int) -> bytes:
    im = Image.open(io.BytesIO(im_bytes)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def gradient(im):
    for x in range(64):
        for y in range(48):
            im.putpixel((x, y), (x * 4) % 256)


def checker(im):
    for x in range(64):
        for y in range(48):
            im.putpixel((x, y), 0 if (x // 8 + y // 8) % 2 else 255)


def test_a_re_encode_of_the_same_photo_lands_within_a_few_bits():
    a = _png(gradient)
    assert hamming(dhash_bytes(a), dhash_bytes(_jpeg(a, 60))) <= 6


def test_two_different_pictures_are_far_apart():
    assert hamming(dhash_bytes(_png(gradient)), dhash_bytes(_png(checker))) > 16


def test_not_an_image_is_no_hash_not_a_crash():
    assert dhash_bytes(b"<html>not a picture</html>") is None


def test_only_public_http_urls_are_fetched():
    """The URL is a publisher's, i.e. an attacker's if the feed is compromised,
    and the worker fetches it from inside the deployment."""
    from common.imagehash import public_http_url

    for bad in ["http://127.0.0.1/x.jpg", "http://169.254.169.254/latest/meta-data", "http://10.0.0.5/a.png", "http://[::1]/a.png", "file:///etc/passwd", "ftp://example.com/a.jpg", "http://localhost/a.jpg", ""]:
        assert public_http_url(bad) is False, bad
    assert public_http_url("https://ichef.bbci.co.uk/ace/ws/800/a.jpg.webp") is True
