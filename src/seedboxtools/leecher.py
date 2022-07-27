"""
This is the code in charge of downloading proper
"""

import errno, os, signal, sys, subprocess, time, traceback
from seedboxtools import util, cli, config
from seedboxtools.clients import TemporaryMalfunction, Misconfiguration
from requests.exceptions import ConnectionError

EXIT_NOTCONFIGURED = 6
EXIT_NOPERMISSION = 4
EXIT_INVALIDARGUMENT = 2
EXIT_CHDIR = 200

# start execution here
def download(client, remove_finished=False, run_processor_program=None):
    for torrent, status, filename in client.get_files_to_download():
        # Set loop vars up
        download_lockfile = ".%s.done" % filename
        fully_downloaded = os.path.exists(download_lockfile)
        seeding = status == "Seeding"

        # If the file is completely downloaded but not to be remotely removed, skip
        if fully_downloaded and not remove_finished:
            util.report_message(
                "%s from %s is fully downloaded, continuing to next torrent"
                % (filename, torrent)
            )
            continue

        # If the remote files don't exist, skip
        util.report_message(
            "Checking if %s from torrent %s exists on server" % (filename, torrent)
        )
        if not client.exists_on_server(filename):
            util.report_message(
                "%s from %s is no longer available on server, continuing to next torrent"
                % (filename, torrent)
            )
            continue

        if not fully_downloaded:

            # Start download.
            util.report_message("Downloading %s from torrent %s" % (filename, torrent))
            util.mark_dir_downloading_when_it_appears(filename)
            retvalue = client.transfer(filename)
            if retvalue != 0:
                # rsync failed
                util.mark_dir_error(filename)
                if retvalue == 20:
                    util.report_error(
                        "Download of %s stopped -- rsync process interrupted"
                        % (filename,)
                    )
                    util.report_message("Finishing by user request")
                    return 2
                elif retvalue < 0:
                    util.report_error(
                        "Download of %s failed -- rsync process killed with signal %s"
                        % (filename, -retvalue)
                    )
                    util.report_message("Aborting")
                    return 1
                else:
                    util.report_error(
                        "Download of %s failed -- rsync process exited with return status %s"
                        % (filename, retvalue)
                    )
                    util.report_message("Aborting")
                    return 1
            # Rsync successful
            # mark file as downloaded
            try:
                open(download_lockfile, "w").write("Done")
            except OSError as e:
                if e.errno != 17:
                    raise
            # report successful download
            fully_downloaded = True
            util.mark_dir_complete(filename)
            util.report_message("Download of %s complete" % filename)

            if run_processor_program is not None:
                try:
                    retval = subprocess.call(
                        [run_processor_program, filename], stdin=open(os.devnull)
                    )
                    util.report_message(
                        "Execution of %s %s exited with return value%s"
                        % (
                            run_processor_program,
                            filename,
                            retval,
                        )
                    )
                except OSError as e:
                    util.report_error(
                        "Program %r is not executable: %s" % (run_processor_program, e)
                    )

        if remove_finished:
            if seeding:
                util.report_message(
                    "%s from %s is complete but still seeding, not removing"
                    % (filename, torrent)
                )
            else:
                client.remove_remote_download(filename)
                try:
                    os.unlink(download_lockfile)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
                util.report_message("Removal of %s complete" % filename)


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


def do_guarded(client, remove_finished, run_processor_program):
    global sighandled
    try:
        return download(
            client=client,
            remove_finished=remove_finished,
            run_processor_program=run_processor_program,
        )
    except IOError as e:
        if e.errno == 4:
            pass
        else:
            traceback.print_exc()
        return 8
    except Misconfiguration as e:
        util.report_error(str(e))
        traceback.print_exc()
        return 16
    except TemporaryMalfunction as e:
        util.report_error(str(e))
    except ConnectionError as e:
        util.report_error(str(e))
    except subprocess.CalledProcessError as e:
        if not sighandled:
            raise
    except Exception as e:
        raise


def mainloop():
    global sighandled

    parser = cli.get_parser()
    opts, args = parser.parse_args()
    util.set_verbose(not opts.quiet)

    # command line parameter checks
    if args:
        parser.error("This command accepts no arguments")

    if opts.lock and opts.lock_homedir:
        parser.error("--lock and --lock-homedir are mutually exclusive")

    if opts.run_every is not False:
        try:
            opts.run_every = int(opts.run_every)
            if opts.run_every < 1:
                raise ValueError
        except ValueError as e:
            parser.error("option --run-every must be a positive integer")

    # check config availability and load configuration
    try:
        config_fobject = open(config.default_filename)
    except (IOError, OSError) as e:
        util.report_error(
            "Cannot load configuration (%s) -- run configleecher first" % (e)
        )
        sys.exit(EXIT_NOTCONFIGURED)
    cfg = config.load_config(config_fobject)
    local_download_dir = cfg.general.local_download_dir
    client = config.get_client(cfg)

    # check download dir and log file availability
    try:
        os.chdir(local_download_dir)
    except (IOError, OSError) as e:
        util.report_error(
            "Cannot change to download directory %r: %s" % (local_download_dir, e)
        )
        sys.exit(EXIT_CHDIR)

    # check processor program availability
    if opts.run_processor_program is not None:
        program = util.executable_exists(opts.run_processor_program)
        if program is None:
            util.report_error(
                "Program %r is not executable" % opts.run_processor_program
            )
            sys.exit(EXIT_INVALIDARGUMENT)

    if opts.logfile:
        try:
            open(opts.logfile, "a")
        except (IOError, OSError) as e:
            util.report_error("Cannot open log file %r: %s" % (opts.logfile, e))
            sys.exit(EXIT_NOPERMISSION)

    # daemonization and preparation
    if opts.daemonize:
        logfile = opts.logfile if opts.logfile else ".torrentleecher.log"
        util.daemonize(logfile)
        # everything else depends on the local_download_dir being the cwd
        os.chdir(local_download_dir)
    elif opts.logfile:
        # non-daemonizing version of the above block
        os.close(1)
        os.close(2)
        sys.stdout = open(opts.logfile, "a")
        sys.stderr = sys.stderr
        os.dup2(1, 2)

    signal.signal(signal.SIGTERM, sighandler)
    signal.signal(signal.SIGINT, sighandler)

    # lockfile check
    if opts.lock or opts.lock_homedir:
        if opts.lock:
            torrentleecher_lockfile = ".torrentleecher.lock"
        else:
            torrentleecher_lockfile = os.path.join(
                os.path.expanduser("~"), ".torrentleecher.lock"
            )
        result = util.lock(torrentleecher_lockfile)
        if not result:
            util.report_error("Another process has a lock on the download directory")
            sys.exit(0)

    dg = lambda: do_guarded(
        client,
        remove_finished=opts.remove_finished,
        run_processor_program=opts.run_processor_program,
    )

    retvalue = 0
    if opts.run_every is False:
        util.report_message("Starting download of finished torrents")
        retvalue = dg()
        util.report_message("Download of finished torrents complete")
    else:
        util.report_message("Starting daemon for download of finished torrents")
        while not sighandled:
            retvalue = dg()
            if not sighandled:
                util.report_message("Sleeping %s seconds" % opts.run_every)
            for _ in range(opts.run_every):
                if not sighandled:
                    time.sleep(1)
        util.report_message("Download of finished torrents complete")
    if sighandled:
        return 0
    return retvalue
