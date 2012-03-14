'''
Command - line helpers for seedboxtools
'''

import os, sys, time, signal, optparse
import traceback
from seedboxtools.clients import client
from seedboxtools import util, downloader

def get_parser():
    '''returns the parser for the command line options'''
    parser = optparse.OptionParser()
    parser.add_option(
        "-g", '--logfile',
        help = "redirect standard output and standard error to log file (relative to download directory; default %default)",
        action = 'store', dest = 'logfile', default = None,
    )
    parser.add_option(
        "-D", '--daemon',
        help = "daemonize after start; useful for cron executions (combined with --lock); implies option -g .torrentleecher.log unless specified otherwise",
        action='store_true', dest='daemonize', default=False,
    )
    parser.add_option(
        "-t", '--run-every',
        help="start up and run forever, looping every X seconds; useful for systemd executions",
        action='store', dest='run_every', default=False
    )
    parser.add_option(
        "-r", '--remove-finished',
        help="remove downloaded torrents that are not seeding anymore",
        action='store_true', dest='remove_finished', default=False
    )
    parser.add_option(
        "-l", '--lock',
        help="lock working directory; useful for cron executions (combine with --daemon to prevent cron from jamming until downloads are finished)",
        action='store_true', dest='lock', default=False
    )
    parser.add_option(
        "-q", '--quiet',
        help="do not print anything, except for errors",
        action='store_true', dest='quiet', default=False
    )
    return parser

sighandled = False
def sighandler(signum, frame):
    global sighandled
    if not sighandled:
        util.report_message("Received signal %s" % signum)
        # temporarily immunize from signals
        oldhandler = signal.signal(signum, signal.SIG_IGN)
        os.killpg(0, signum)
        signal.signal(signum, oldhandler)
        sighandled = True

def mainloop():
    global sighandled

    parser = get_parser()
    opts, args = parser.parse_args()
    util.set_verbose(not opts.quiet)

    # command line parameter checks
    if args: parser.error("This command accepts no arguments")

    if opts.run_every is not False:
        try:
            opts.run_every = int(opts.run_every)
            if opts.run_every < 1:
                raise ValueError
        except ValueError, e:
            parser.error("option --run-every must be a positive integer")

    try:
        os.chdir(client.local_download_dir)
    except (IOError, OSError), e:
        util.report_error("Cannot change to download directory %r: %s" % (client.local_download_dir, e))
        sys.exit(4)

    if opts.logfile:
        try:
            file(opts.logfile, "a", 0)
        except (IOError, OSError), e:
            util.report_error("Cannot open log file %r: %s" % (opts.logfile, e))
            sys.exit(4)

    # daemonization and preparation
    if opts.daemonize:
        logfile = opts.logfile if opts.logfile else ".torrentleecher.log"
        util.daemonize(logfile)
        # everything else depends on the local_download_dir being the cwd
        os.chdir(client.local_download_dir)
    elif opts.logfile:
        # non-daemonizing version of the above block
        os.close(1)
        os.close(2)
        sys.stdout = file(opts.logfile, "a", 0)
        sys.stderr = sys.stderr
        os.dup2(1, 2)

    signal.signal(signal.SIGTERM, sighandler)
    signal.signal(signal.SIGINT, sighandler)

    # lockfile check
    if opts.lock:
            torrentleecher_lockfile = ".torrentleecher.lock"
            result = util.lock(torrentleecher_lockfile)
            if not result:
                util.report_error("Another process has a lock on the download directory")
                sys.exit(0)

    def do_guarded():
        try:
            return downloader.download(
               client=client,
               remove_finished=opts.remove_finished
            )
        except IOError, e:
            if e.errno == 4: pass
            else: traceback.print_last()
            return 8
        except Exception, e:
            raise

    retvalue = 0
    if opts.run_every is False:
        util.report_message("Starting download of finished torrents")
        retvalue = do_guarded()
        util.report_message("Download of finished torrents complete")
    else:
        util.report_message("Starting daemon for download of finished torrents")
        while not sighandled:
            retvalue = do_guarded()
            if not sighandled: util.report_message("Sleeping %s seconds" % opts.run_every)
            for x in xrange(opts.run_every):
                if not sighandled: time.sleep(1)
        util.report_message("Download of finished torrents complete")
    if sighandled: return 0
    return retvalue
