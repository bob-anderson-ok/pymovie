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
