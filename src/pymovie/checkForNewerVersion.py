def getMostRecentVersionOfPyMovie():

    import subprocess

    # The call to pip that follows utilizes a trick: when pip is given a valid package but an
    # invalid version number, it writes to stderr an error message that contains a list of
    # all available versions.
    # Below is an example capture...

    # Could not find a version that satisfies the requirement
    #   pymovie==?? (from versions: 1.11, 1.12, 1.13, 1.14, 1.15, 1.16)

    resp = None
    # noinspection PyBroadException
    try:
        resp = subprocess.run(['python', '-m', 'pip', 'install', 'pymovie==??'],
                          stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    except:
        pass

    # Convert the byte array to a string and split into lines
    ans = resp.stderr.decode("utf-8").split('\n')

    # Split the first line of the response into its sub-strings
    ans = ans[0].split()

    if ans[0] == 'Retrying':
        return False, 'No Internet connection --- could not reach PyPI'
    elif not (ans[0] == 'Could' or ans[1] == 'Could'):
        # The above test accomodates the return from pip version 18.1 AND version 19.0+
        return False, 'Failed to find pymovie package in PyPI repository'
    else:
        versionFound = ans[-1][0:-1]  # Use last string, but not the trailing right paren
        return True, versionFound


def upgradePyMovie(pymovieversion):

    import subprocess

    resp = subprocess.run(['python', '-m', 'pip', 'install', '--user', '--upgrade', pymovieversion],
                          stderr=subprocess.PIPE, stdout=subprocess.PIPE)

    ans = resp.stdout.decode("utf-8").split('\n')

    return ans
