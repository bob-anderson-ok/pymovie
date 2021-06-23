import subprocess
import json, re
import urllib.request, urllib.error, urllib.parse
from distutils.version import StrictVersion

def getMostRecentVersionOfPyMovieViaJason():

    #!!!!! Many thanks to Kia Getrost for supplying this much improved version of 'getMostRecentVersionOfPymovie'

    # Returns tuple of gotVersion, latestVersion
    # (boolean and version-or-error string)

    pkgName = "pymovie"

    # Do a JSON request to pypi to get latest version:
    url = f"https://pypi.org/pypi/{pkgName}/json"
    text = getUrlAsText(url)
    if text is None:
        return False, "Could not contact pypi.org to check for latest version"

    # Parse the JSON result:
    try:
        data = json.loads(text)
    except ValueError:
        return False, "Could not parse JSON response from pypi.org"

    # Sort versions to get the latest:
    versions = sorted(data["releases"], key=StrictVersion, reverse=True)
    latestVersion = versions[0]

    # Ensure we have a seemingly valid vesrion number:
    if not re.match(r"\d+\.\d+\.\d+", latestVersion):
        return False, f"Garbled version `{latestVersion}' from pypi.org"

    # All is well, return result:
    return True, latestVersion

def getUrlAsText(url):
    # Returns text string of `url', or None on error

    try:
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)
    except urllib.error.URLError as exception:
        if hasattr(exception, "reason"):
            print(f"Fetch of `{url}' failed: {exception.reason}")
        elif hasattr(exception, "code"):
            print(f"Fetch of `{url}' failed: returned HTTP code {exception.code}")
        else:
            print(f"Fetch of `{url}' failed: Unknown reason")
        return None
    html = response.read()
    text = html.decode("utf-8")
    return text

def upgradePyMovie(pymovieversion):

    import subprocess

    resp = subprocess.run(['python', '-m', 'pip', 'install', '--user', '--upgrade', pymovieversion],
                          stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    ans = resp.stdout.decode("utf-8").split('\n')

    return ans
