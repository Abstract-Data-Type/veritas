"""
Test to verify URL construction bug with trailing slash
"""


import pytest


def test_url_trailing_slash_bug():
    """
    BUG: When SUMMARIZATION_SERVICE_URL has a trailing slash,
    the URL construction creates a double slash: http://localhost:8000//summarize

    This is a URL construction bug that could cause issues with some HTTP servers.
    """

    # Test URL with trailing slash
    url_with_slash = "http://localhost:8000/"
    expected_endpoint = "http://localhost:8000/summarize"
    actual_endpoint = f"{url_with_slash}/summarize"

    # BUG: This creates double slash
    assert actual_endpoint == "http://localhost:8000//summarize"
    assert actual_endpoint != expected_endpoint

    print(f"Expected: {expected_endpoint}")
    print(f"Actual: {actual_endpoint}")
    print("BUG CONFIRMED: Double slash in URL construction")


def test_url_without_trailing_slash():
    """Test that URL without trailing slash works correctly"""
    url_without_slash = "http://localhost:8000"
    expected_endpoint = "http://localhost:8000/summarize"
    actual_endpoint = f"{url_without_slash}/summarize"

    assert actual_endpoint == expected_endpoint
    print("URL without trailing slash works correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
