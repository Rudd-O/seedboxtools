#!/usr/bin/env python
"""Subprocess utilities for seedboxtools"""


# subprocess utilities

from subprocess import Popen, PIPE, STDOUT, call
import os, sys
import fcntl

def shell_quote(shellarg):
        return"'%s'" % shellarg.replace("'", r"'\''")

def getstdout(cmdline):
        p = Popen(cmdline, stdout=PIPE)
        output = p.communicate()[0]
        if p.returncode != 0: raise Exception, "Command %s return code %s" % (cmdline, p.returncode)
        return output

def getstdoutstderr(cmdline, inp=None): # return stoud and stderr in a single string object
        p = Popen(cmdline, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        output = p.communicate(inp)[0]
        if p.returncode != 0: raise Exception, "Command %s return code %s" % (cmdline, p.returncode)
        return output

def passthru(cmdline):
    return call(cmdline) # return status code, pass the outputs thru

def quote_cmdline(cmdline):
    """Quote a command line in list form for SSH usage"""
    return " ".join(shell_quote(x) for x in cmdline)

def ssh_getstdout(hostname, cmdline):
    cmd = quote_cmdline(cmdline)
    return getstdout(["ssh", "-o", "BatchMode yes", "-o", "ForwardX11 no", hostname, cmd])

def ssh_passthru(hostname, cmdline):
    cmd = quote_cmdline(cmdline)
    return passthru(["ssh", "-o", "BatchMode yes", "-o", "ForwardX11 no", hostname, cmd])

def firstcomponent(path):
    if not path: raise ValueError, "path cannot be empty: %r" % path
    oldpath = path
    while True:
        path = os.path.dirname(path)
        if not path or os.path.dirname(path) == path: break
        oldpath = path
    return oldpath

# unix process utilities

def daemonize(logfile=os.devnull):
    """Detach a process from the controlling terminal and run it in the
    background as a daemon.
    """

    pwd = os.getcwd()
    logfile = os.path.join(pwd, logfile)

    try: pid = os.fork()
    except OSError, e: raise Exception, "%s [%d]" % (e.strerror, e.errno)

    if (pid == 0):         # The first child.
        os.setsid()
        try: pid = os.fork()          # Fork a second child.
        except OSError, e: raise Exception, "%s [%d]" % (e.strerror, e.errno)

        if (pid == 0):     # The second child.
            os.chdir("/")
        else:
            # exit() or _exit()?  See below.
            os._exit(0)     # Exit parent (the first child) of the second child.
    else: os._exit(0)         # Exit parent of the first child.

    import resource                  # Resource usage information.
    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if (maxfd == resource.RLIM_INFINITY):
        maxfd = 1024

    # Iterate through and close all file descriptors.
    for f in [ sys.stderr, sys.stdout, sys.stdin ]:
        try: f.flush()
        except: pass

    for fd in range(0, 2):
        try: os.close(fd)
        except OSError: pass

    for f in [ sys.stderr, sys.stdout, sys.stdin ]:
        try: f.close()
        except: pass

    sys.stdin = file("/dev/null", "r")
    sys.stdout = file(logfile, "a", 0)
    sys.stderr = file(logfile, "a", 0)
    os.dup2(1, 2)

    return(0)

def lock(lockfile):
    global f
    try:
        fcntl.lockf(f.fileno(), fcntl.LOCK_UN)
        f.close()
    except: pass
    try:
        f = open(lockfile, 'w')
        fcntl.lockf(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError, e:
        if e.errno == 11: return False
        else: raise
    return True



# icon-setting utilities

from threading import Thread
import time

def set_dir_icon(filename, iconname):
    text = """[Desktop Entry]
Icon = % s
""" % iconname
    try: file(os.path.join(filename, ".directory"), "w").write(text)
    except: pass

def mark_dir_complete(filename): set_dir_icon(filename, "dialog-ok-apply.png")
def mark_dir_downloading(filename): set_dir_icon(filename, "document-open-remote.png")
def mark_dir_error(filename): set_dir_icon(filename, "dialog-cancel.png")

def mark_dir_downloading_when_it_appears(filename):
    isdir = os.path.isdir
    tiem = time.time
    sleep = time.sleep
    starttime = tiem()
    def dowatch():
            while not isdir(filename) and tiem() - starttime < 600: sleep(0.1)
            if isdir(filename): mark_dir_downloading(filename)
    tehrd = Thread(target=dowatch)
    tehrd.setDaemon(True)
    tehrd.start()

# tts utilities

def speakize(filename):
    try:
        filename, extension = os.path.splitext(filename)
        if len(extension) != 3: filename = filename + "." + extension
    except ValueError: pass
    for char in "[]{}.,-_": filename = filename.replace(char, " ")
    return filename

def speak(text):
    return passthru(["/usr/local/bin/speak-notification", "-n", "William", text])

# message reporting utilities

verbose = True
def set_verbose(v):
    global verbose
    verbose = v

def report_message(text):
    global verbose
    if verbose: print text

def report_error(text):
    print text
