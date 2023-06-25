import random
import threading
import time
import html2text
from markdown import markdown
from bleach import clean

class RateLimiter:
    """Synchronous rate limiting."""
    def __init__(self, max_calls_per_second: float, *, init_backoff_time: float=0.1) -> None:
        self.call_interval = 1.0 / max_calls_per_second
        self.last_call_time_monotonic = 0.0
        self.lock = threading.Lock()
        self.backoff_time = init_backoff_time

    def wait(self) -> None:
        while True:
            with self.lock:
                # Calculate the time elapsed since the last call
                elapsed_time = time.monotonic() - self.last_call_time_monotonic

                # If the appropriate time has elapsed
                if elapsed_time >= self.call_interval:
                    self.last_call_time_monotonic = time.monotonic()
                    self.backoff_time = 0.1  # Reset backoff time
                    return

            # If not enough time has elapsed, wait
            time_to_wait = max(self.call_interval - elapsed_time, self.backoff_time)
            # Add a random jitter
            jitter = time_to_wait * random.uniform(0.5, 1.5)
            time.sleep(time_to_wait + jitter)
            # Update exponential backoff time
            self.backoff_time *= 2


def render_bs4_element_to_markdown(bs4_elem) -> str:
    """Convert a BeautifulSoup4 element to Markdown using html2text."""
    h = html2text.HTML2Text()
    h.body_width = 0  # Disable text wrapping
    h.ignore_images = True
    h.ignore_links = True
    h.ignore_tables = True
    return h.handle(str(bs4_elem))


def safe_markdown_render(markdown_src: str) -> str:
    """Safely render Markdown to HTML, ensuring that there's no hidden JS and no
    images (or other tags that could load external resources)."""
    html = markdown(markdown_src)
    return clean(html, tags=['div', 'span', 'p', 'em', 'strong', 'code', 'pre'], protocols=[])