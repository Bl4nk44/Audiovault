from app.utils.sanitization import sanitize_filename


def test_sanitize_filename_basic():
    assert sanitize_filename("normal.txt") == "normal.txt"


def test_sanitize_filename_with_slashes():
    result = sanitize_filename("path/to/file.txt")
    assert "/" not in result
    assert "\\" not in result


def test_sanitize_filename_with_special_chars():
    result = sanitize_filename("file:name*test?.txt")
    assert ":" not in result
    assert "*" not in result
    assert "?" not in result


def test_sanitize_filename_with_quotes():
    result = sanitize_filename('file"name<test>.txt')
    assert '"' not in result
    assert "<" not in result
    assert ">" not in result


def test_sanitize_filename_empty():
    result = sanitize_filename("")
    assert result == "" or result is not None


def test_sanitize_filename_unicode():
    result = sanitize_filename("Zażółć gęślą jaźń.mp3")
    assert isinstance(result, str)
    assert ".mp3" in result


def test_sanitize_filename_long():
    long_name = "a" * 300 + ".mp3"
    result = sanitize_filename(long_name)
    assert len(result) <= 255
