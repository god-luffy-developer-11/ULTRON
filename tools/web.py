"""Web browsing, search, and downloading tools."""
import urllib.parse
import webbrowser
import requests
from tools.pc_control import run_shell

def search_web(query: str) -> str:
    """Perform a web search by opening default browser with results."""
    encoded = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={encoded}"
    webbrowser.open(url)
    return f"Opened web search for '{query}'."

def open_url(url: str) -> str:
    """Open a URL in the browser."""
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}."

def download_file(url: str, destination: str) -> str:
    """Download a file from the web."""
    try:
        resp = requests.get(url, stream=True, timeout=20)
        if resp.status_code == 200:
            with open(destination, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return f"Downloaded to {destination}."
        return f"Download failed with status {resp.status_code}."
    except Exception as e:
        return f"Download error: {e}"
