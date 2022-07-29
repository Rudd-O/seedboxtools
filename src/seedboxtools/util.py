"""Subprocess utilities for seedboxtools"""


# subprocess utilities

from subprocess import Popen, PIPE, STDOUT, call, check_call
import os
import sys
import fcntl
from threading import Thread
import time


def shell_quote(shellarg):
    return "'%s'" % shellarg.replace("'", r"'\''")


def getstdout(cmdline):
    p = Popen(cmdline, stdout=PIPE)
    output = p.communicate()[0].decode("utf-8")
    if p.returncode != 0:
        raise Exception("Command %s return code %s" % (cmdline, p.returncode))
    return output


def getstdoutstderr(
    cmdline, inp=None
):  # return stoud and stderr in a single string object
    p = Popen(cmdline, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    output = p.communicate(inp)[0].decode("utf-8")
    if p.returncode != 0:
        raise Exception("Command %s return code %s" % (cmdline, p.returncode))
    return output


def passthru(cmdline: list[str]) -> int:
    return call(cmdline)  # return status code, pass the outputs thru


def rsync(source: str, destination: str) -> int:
    RSYNC_OPTS = ["-rtlDvzP", "--chmod=go+rX", "--chmod=u+rwX", "--executability"]
    cmdline = ["rsync"] + RSYNC_OPTS + ["--", source, destination]
    return passthru(cmdline)


def quote_cmdline(cmdline):
    """Quote a command line in list form for SSH usage"""
    return " ".join(shell_quote(x) for x in cmdline)


def ssh_getstdout(hostname, cmdline):
    cmd = quote_cmdline(cmdline)
    return getstdout(
        ["ssh", "-o", "BatchMode yes", "-o", "ForwardX11 no", hostname, cmd]
    )


def ssh_passthru(hostname, cmdline):
    cmd = quote_cmdline(cmdline)
    return passthru(
        ["ssh", "-o", "BatchMode yes", "-o", "ForwardX11 no", hostname, cmd]
    )


def firstcomponent(path):
    if not path:
        raise ValueError("path cannot be empty: %r" % path)
    oldpath = path
    while True:
        path = os.path.dirname(path)
        if not path or os.path.dirname(path) == path:
            break
        oldpath = path
    return oldpath


# unix process utilities


def daemonize(logfile=os.devnull):
    """Detach a process from the controlling terminal and run it in the
    background as a daemon.
    """

    pwd = os.getcwd()
    logfile = os.path.join(pwd, logfile)

    try:
        pid = os.fork()
    except OSError as e:
        raise Exception("%s [%d]" % (e.strerror, e.errno))

    if pid == 0:  # The first child.
        os.setsid()
        try:
            pid = os.fork()  # Fork a second child.
        except OSError as e:
            raise Exception("%s [%d]" % (e.strerror, e.errno))

        if pid == 0:  # The second child.
            os.chdir("/")
        else:
            # exit() or _exit()?  See below.
            os._exit(0)  # Exit parent (the first child) of the second child.
    else:
        os._exit(0)  # Exit parent of the first child.

    import resource  # Resource usage information.

    maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if maxfd == resource.RLIM_INFINITY:
        maxfd = 1024

    # Iterate through and close all file descriptors.
    for f in [sys.stderr, sys.stdout, sys.stdin]:
        try:
            f.flush()
        except BaseException:
            pass

    for fd in range(0, 2):
        try:
            os.close(fd)
        except OSError:
            pass

    for f in [sys.stderr, sys.stdout, sys.stdin]:
        try:
            f.close()
        except BaseException:
            pass

    sys.stdin = open("/dev/null", "r")
    sys.stdout = open(logfile, "a")
    sys.stderr = open(logfile, "a")
    os.dup2(1, 2)

    return 0


def lock(lockfile):
    global f
    try:
        fcntl.lockf(f.fileno(), fcntl.LOCK_UN)
        f.close()
    except BaseException:
        pass
    try:
        f = open(lockfile, "w")
        fcntl.lockf(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as e:
        if e.errno == 11:
            return False
        else:
            raise
    return True


# icon-setting utilities


def set_dir_icon(filename, iconname):
    text = (
        """[Desktop Entry]
Icon = % s
"""
        % iconname
    )
    try:
        open(os.path.join(filename, ".directory"), "w").write(text)
    except BaseException:
        pass


def mark_dir_complete(filename):
    set_dir_icon(filename, "dialog-ok-apply.png")


def mark_dir_downloading(filename):
    set_dir_icon(filename, "document-open-remote.png")


def mark_dir_error(filename):
    set_dir_icon(filename, "dialog-cancel.png")


def mark_dir_downloading_when_it_appears(filename):
    isdir = os.path.isdir
    tiem = time.time
    sleep = time.sleep
    starttime = tiem()

    def dowatch():
        while not isdir(filename) and tiem() - starttime < 600:
            sleep(0.1)
        if isdir(filename):
            mark_dir_downloading(filename)

    tehrd = Thread(target=dowatch)
    tehrd.setDaemon(True)
    tehrd.start()


# message reporting utilities


def which(program):
    import os

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def notify_send(message, transient=True):
    cmd = [
        "notify-send",
        "-a",
        os.path.basename(sys.argv[0]),
        "Seedbox tools",
        message,
    ]
    if transient:
        cmd.append("--hint=int:transient:1")
    return check_call(cmd)


_use_linux_gui = None


def use_linux_gui():
    global _use_linux_gui
    if _use_linux_gui is None:
        if os.environ.get("DISPLAY", None) and which("notify-send"):
            _use_linux_gui = True
        else:
            _use_linux_gui = False
    return _use_linux_gui


verbose = True


def set_verbose(v):
    global verbose
    verbose = v


def report_message(text):
    global verbose
    if verbose:
        if use_linux_gui():
            notify_send(text.capitalize())
        print(text, file=sys.stderr)


def report_error(text):
    if use_linux_gui():
        notify_send(text.capitalize(), transient=False)
    print(text, file=sys.stderr)


def executable_exists(path):
    """Checks that an executable is executable, along PATH
    or, if specified as relative or absolute path name, directly."""
    envpath = os.getenv("PATH", "/usr/local/bin:/usr/bin:/bin")
    PATH = envpath.split(os.path.pathsep)
    for d in PATH:
        if os.path.sep in path:
            fullname = path
        else:
            fullname = path.join(d, path)
        if os.access(fullname, os.X_OK):
            return fullname
    return None
