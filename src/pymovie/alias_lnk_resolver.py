import subprocess
import os
import shlex


# returns the full path of the file "pointed to" by the alias
def resolve_osx_alias(path):        # single file/path name
    checkpath = os.path.abspath(path)       # osascript needs absolute paths
    # Next several lines are AppleScript
    line_1='tell application "Finder"'
    line_2='set theItem to (POSIX file "'+checkpath+'") as alias'
    line_3='if the kind of theItem is "alias" then'
    line_4='   get the posix path of (original item of theItem as text)'
    line_5='else'
    line_6='return "'+checkpath+'"'
    line_7 ='end if'
    line_8 ='end tell'
    cmd = "osascript -e '"+line_1+"' -e '"+line_2+"' -e '"+line_3+"' -e '"+line_4+"' -e '"+line_5+"' -e '"+line_6+"' -e '"+line_7+"' -e '"+line_8+"'"
    # shlex splits cmd up appropriately so we can call subprocess.Popen with shell=False (better security)
    args = shlex.split(cmd)
    p = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    retval = p.wait()
    if retval == 0:
        line = p.stdout.readlines()[0]
        source = line.decode('UTF-8').replace('\n','')
        # if (convert):
        #     os.remove(checkpath)
        #     os.symlink(source, checkpath)
    else:
        print('resolve_osx_aliases: Error: subprocess returned non-zero exit code '+str(retval))
        source = ''
    return source


def create_osx_alias_in_dir(file_path, dir_path):
    theFile = os.path.abspath(file_path)   # osascript needs absolute paths
    theDir = os.path.abspath(dir_path)
    line1 = 'tell application "Finder"'
    line2 = '  make new alias file at (POSIX file "'+theDir+'") to (POSIX file "'+theFile+'" as alias)'
    line3 = 'end tell'
    cmd = "osascript -e '"+line1+"' -e '"+line2+"' -e '"+line3+"'"
    args = shlex.split(cmd)
    p = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    retval = p.wait()
    if retval == 0:
        line = p.stdout.readlines()[0]
        source = line.decode('UTF-8').replace('\n', '')
        return True, theFile, theDir, retval, source
    else:
        line = p.stdout.readlines()[0]
        source = line.decode('UTF-8').replace('\n', '')
        return False, theFile, theDir, retval, source

