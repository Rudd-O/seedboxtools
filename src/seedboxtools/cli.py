'''
Command - line helpers for seedboxtools
'''

import argparse
import optparse

def get_parser():
    '''returns the parser for the command line options'''
    parser = optparse.OptionParser()
    parser.add_option(
        "-g", '--logfile',
        help="redirect standard output and standard error to log file (relative to download directory; default %default)",
        action='store', dest='logfile', default=None,
    )
    parser.add_option(
        "-D", '--daemon',
        help="daemonize after start; useful for cron executions (combined with --lock); implies option -g .torrentleecher.log unless specified otherwise",
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
        "-s", '--run-processor-program',
        help="run program after completing download, passing path to download as first argument",
        action='store', dest='run_processor_program', default=None
    )
    parser.add_option(
        "-l", '--lock',
        help="lock working directory; useful for cron executions (combine with --daemon to prevent cron from jamming until downloads are finished)",
        action='store_true', dest='lock', default=False
    )
    parser.add_option(
        "-H", '--lock-homedir',
        help="lock home directory; alternative (mutually exclusive) to --lock",
        action='store_true', dest='lock_homedir', default=False
    )
    parser.add_option(
        "-q", '--quiet',
        help="do not print anything, except for errors",
        action='store_true', dest='quiet', default=False
    )
    return parser

def get_uploader_parser():
    '''returns argument parser for uploader tool'''
    parser = argparse.ArgumentParser(description='Upload torrents and magnet links to seedbox.')
    parser.add_argument('-d', '--debug', action="store_true", default=False,
                        help='enable tracebacks for errors')
    parser.add_argument('torrents', metavar='TORRENT', nargs='+',
                        help='torrent file or magnet link')
    return parser
