from app.core.storage import public_url


def test_public_url_keeps_absolute_urls():
    assert public_url("https://example.com/logo.png") == "https://example.com/logo.png"
