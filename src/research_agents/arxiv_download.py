import threading
import requests
import time
import random
import re
import dbm
import textwrap
import os
import pathlib

from research_agents.utils import RateLimiter


_global_arxiv_rate_limiter = RateLimiter(1.0)  # limit to 1 req/s
_arxiv_cache_path = pathlib.Path(__file__).absolute().parent.parent.parent / 'arxiv_cache.dbm'


def download_arxiv_html(arxiv_identifier: str, *, timeout: float=10.0) -> str:
    """Download the HTML of an arXiv paper via ar5iv.
    
    Args:
        arxiv_identifier: A numeric identify (XXXX.YYYYY) or arXiv URL
            identifying the paper.
        timeout: The maximum time to wait for a response from the server.
        
    Returns:
        The HTML of the paper as a string."""

    identifier_re = re.compile(r".*\b(?P<numeric_id>[0-9]{4}\.[0-9]{5})(v[0-9]+)?\b.*")
    match = identifier_re.match(arxiv_identifier)
    if match is None:
        raise ValueError("Invalid arXiv identifier: {}".format(arxiv_identifier))

    # get the numeric ID (without the optional version)
    numeric_id = match.group("numeric_id")

    # check the local cache
    with dbm.open(str(_arxiv_cache_path), 'c') as cache:
        if numeric_id in cache:
            return cache[numeric_id].decode("utf-8")

    # construct ar5iv URL
    ar5iv_url = f"https://ar5iv.labs.arxiv.org/html/{numeric_id}"

    # be kind
    _global_arxiv_rate_limiter.wait()

    response = requests.get(ar5iv_url, timeout=timeout, allow_redirects=True)
    if response.status_code != 200:
        raise ValueError(f"Server gave status code {response.status_code} for {ar5iv_url}")

    # write response text to local cache
    with dbm.open(str(_arxiv_cache_path), 'c') as cache:
        cache[numeric_id] = response.text.encode("utf-8")

    return response.text

# def find_paper_on_arxiv(*, title: Optional[str] = None, authors: Optional[str] = None, year: Optional[str] = None) -> str:
#     pass

if __name__ == '__main__':
    # fetch some papers as a test
    start = time.time()
    assert "CURL" in download_arxiv_html("2004.04136")
    print(f"Downloaded 2004.04136 in {time.time() - start} seconds")
    start = time.time()
    assert "CURL" in download_arxiv_html("https://arxiv.org/pdf/2004.04136v1.pdf")
    print(f"Downloaded 2004.04136v1 in {time.time() - start} seconds (cached?)")

    print("Page content (first 1024 chars):")
    # wrap text to 50 chars and indent by four spaces
    print(textwrap.indent(textwrap.fill(download_arxiv_html("2004.04136")[:1024], 50), "    "))