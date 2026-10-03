import json
import urllib.error
import urllib.request

_RELEASES_API_URL = "https://api.github.com/repos/bob-anderson-ok/pymovie/releases/latest"
_TIMEOUT_SECONDS = 5


def getLatestPackageVersion(package_name: str) -> str:
    """Return the latest published PyMovie version (e.g. '4.1.7').

    On any failure, returns a string beginning with 'Failed' so the caller
    can display it verbatim. The `package_name` argument is accepted for
    backward compatibility but ignored — the repository is fixed.
    """
    try:
        request = urllib.request.Request(
            _RELEASES_API_URL,
            headers={"Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "Failed: no published releases found on GitHub yet"
        return f"Failed: GitHub returned HTTP {e.code}"
    except urllib.error.URLError as e:
        return f"Failed to reach GitHub ({e.reason}) - Internet connection problem?"
    except (ValueError, TimeoutError) as e:
        return f"Failed to parse GitHub response: {e}"

    tag = payload.get("tag_name", "")
    if not tag:
        return "Failed: GitHub response did not include a tag_name"
    return tag.lstrip("vV")


_RELEASES_LIST_URL = "https://api.github.com/repos/bob-anderson-ok/pymovie/releases?per_page=50"
RELEASES_PAGE_URL = "https://github.com/bob-anderson-ok/pymovie/releases"
README_URL = "https://github.com/bob-anderson-ok/pymovie"


def getReleases():
    """Return (releases, error) for all published releases, newest first.

    Each release is a dict with keys version, name, date (YYYY-MM-DD), notes, page_url and
    exe_url (the PyMovie.exe download link, or None if the release has no such asset).
    Drafts and pre-releases are left out. On failure releases is None and error says why.
    """
    try:
        request = urllib.request.Request(
            _RELEASES_LIST_URL,
            headers={"Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return None, f"GitHub returned HTTP {e.code}"
    except urllib.error.URLError as e:
        return None, f"Could not reach GitHub ({e.reason}) - Internet connection problem?"
    except (ValueError, TimeoutError) as e:
        return None, f"Could not read the GitHub response: {e}"

    releases = []
    for rel in payload:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        version = rel.get("tag_name", "").lstrip("vV")
        if not version:
            continue
        exe_url = None
        for asset in rel.get("assets", []):
            if asset.get("name", "").lower() == "pymovie.exe":
                exe_url = asset.get("browser_download_url")
        releases.append({
            "version": version,
            "name": rel.get("name") or version,
            "date": (rel.get("published_at") or "")[:10],
            "notes": (rel.get("body") or "").replace("\r\n", "\n").strip(),
            "page_url": rel.get("html_url") or RELEASES_PAGE_URL,
            "exe_url": exe_url,
        })
    releases.sort(key=lambda r: _versionKey(r["version"]), reverse=True)
    return releases, None


def _versionKey(v):
    try:
        return tuple(int(n) for n in v.split('.'))
    except ValueError:
        return ()


def isNewerVersion(latest: str, current: str) -> bool:
    """True if `latest` is strictly newer than `current`.

    Compares versions as tuples of integers ('4.1.10' > '4.1.9'). Falls back
    to a string compare if either side isn't pure dotted-integer.
    """
    def asTuple(v):
        try:
            return tuple(int(n) for n in v.split('.'))
        except ValueError:
            return None

    latestT = asTuple(latest)
    currentT = asTuple(current)
    if latestT is None or currentT is None:
        return latest > current
    return latestT > currentT
