from news_scraper.article import extract_text


def test_extract_text_removes_obvious_page_chrome() -> None:
    html = """
    <html>
      <head><title>Important Company News</title><script>alert("x")</script></head>
      <body>
        <nav>Subscribe now</nav>
        <h1>Boom raises $15M</h1>
        <p>Boom works with 400+ operators and about 500,000 units.</p>
        <footer>Contact us</footer>
      </body>
    </html>
    """

    text = extract_text(html)

    assert "Important Company News" in text
    assert "Boom works with 400+ operators" in text
    assert "Subscribe now" not in text
    assert "alert" not in text
