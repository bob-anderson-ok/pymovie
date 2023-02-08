# import subprocess
# import sys
# import json, re
# import urllib.request, urllib.error, urllib.parse
# from distutils.version import StrictVersion

# 23 July 2022 It appears that the PyPI JSON API is no longer working in a way that enables
# us to find the version number of the latest pymovie in the PyPI repository, so we are
# removing it from use.
# def getMostRecentVersionOfPyMovieViaJason():
#
#     #!!!!! Many thanks to Kai Getrost for supplying this much improved version of 'getMostRecentVersionOfPymovie'
#
#     # Returns tuple of gotVersion, latestVersion
#     # (boolean and version-or-error string)
#
#     pkgName = "pymovie"
#
#     # Do a JSON request to pypi to get the latest version:
#     url = f"https://pypi.org/pypi/{pkgName}/json"
#     text = getUrlAsText(url)
#     if text is None:
#         return False, "Could not contact pypi.org to check for latest version"
#
#     # Parse the JSON result:
#     try:
#         data = json.loads(text)
#     except ValueError:
#         return False, "Could not parse JSON response from pypi.org"
#
#     # Sort versions to get the latest:
#     versions = sorted(data["releases"], key=StrictVersion, reverse=True)
#     latestVersion = versions[0]
#
#     # Ensure we have a seemingly valid version number:
#     if not re.match(r"\d+\.\d+\.\d+", latestVersion):
#         return False, f"Garbled version `{latestVersion}' from pypi.org"
#
#     # All is well, return result:
#     return True, latestVersion

# def getUrlAsText(url):
#     # Returns text string of `url', or None on error
#
#     try:
#         request = urllib.request.Request(url)
#         response = urllib.request.urlopen(request)
#     except urllib.error.URLError as exception:
#         if hasattr(exception, "reason"):
#             print(f"Fetch of `{url}' failed: {exception.reason}")
#         elif hasattr(exception, "code"):
#             print(f"Fetch of `{url}' failed: returned HTTP code {exception.code}")
#         else:
#             print(f"Fetch of `{url}' failed: Unknown reason")
#         return None
#     html = response.read()
#     return html.decode("utf-8")

def upgradePyMovie(pymovieversion):

    import subprocess

    resp = subprocess.run(['python', '-m', 'pip', 'install', '--user', '--upgrade', pymovieversion],
                          stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    return resp.stdout.decode("utf-8").split('\n')


# The following function was added 23 July 2022 when (apparently) the PyPI JSON API broke.
# This uses a reliable, supported technique to get info (we are only interested in Version: )
# about a package on PyPI
# def getLatestPackageVersion(package_name: str) -> str:
#     import subprocess
#     response = subprocess.run(['python3', '-m', 'pip', 'install', f"{package_name}==0.0.0"],
#                               stderr=subprocess.PIPE, stdout=subprocess.PIPE)
#     errorResponse = response.stderr.decode("utf-8").split('\n')[0]
#
#     versions = errorResponse.split('versions: ')
#     if len(versions) == 1:  # Because the split above failed
#         # Failed to make Internet connection
#         return 'Failed to connect to PyPI - Internet connection problem?'
#     versions = versions[1].split(')')[0]  # Remove everything at and after ')'
#     latestVersion = versions.split(',')[-1].strip()
#     return latestVersion

def getLatestPackageVersion(package_name: str) -> str:
    import subprocess
    try:
        response = subprocess.run(['python', '-m', 'pip', 'install', f"{package_name}==0.0.0"],
                                  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        errorResponse = response.stderr.decode("utf-8")
        versions = errorResponse.split('versions: ')
    except FileNotFoundError as e:
        print(f'{e}')
        versions = [0]
    if len(versions) == 1:  # Because the split above failed
        print('python not used to start pyote or no internet connection')
        try:
            response = subprocess.run(['python3', '-m', 'pip', 'install', f"{package_name}==0.0.0"],
                                      stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            errorResponse = response.stderr.decode("utf-8")
            versions = errorResponse.split('versions: ')
        except FileNotFoundError as e:
            print(f'{e}')
            versions = [0]
        if len(versions) == 1:
            print('python3 not used to start pyote or no internet connection')
            try:
                response = subprocess.run(['py', '-m', 'pip', 'install', f"{package_name}==0.0.0"],
                                          stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                errorResponse = response.stderr.decode("utf-8")
                versions = errorResponse.split('versions: ')
            except FileNotFoundError as e:
                print(f'{e}')
                versions = [0]
            if len(versions) == 1:
                print('py not used to start pyote or no internet connection')
                # Failed to make Internet connection
                return 'Failed to connect to PyPI - Internet connection problem?'
    versions = versions[1].split(')')[0]  # Remove everything at and after ')'
    latestVersion = versions.split(',')[-1].strip()

    return latestVersion
