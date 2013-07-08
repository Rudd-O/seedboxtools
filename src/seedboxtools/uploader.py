from seedboxtools import cli, config, util
from requests.exceptions import ConnectionError
import os
import sys

def main():
    parser = cli.get_uploader_parser()
    args = parser.parse_args()

    # check config availability and load configuration
    try:
        config_fobject = open(config.default_filename)
    except (IOError, OSError), e:
        util.report_error("Cannot load configuration (%s) -- run configleecher first" % (e))
        sys.exit(7)
    cfg = config.load_config(config_fobject)
    local_download_dir = cfg.general.local_download_dir
    client = config.get_client(cfg)

    # separate the wheat from the chaff
    # and when I say 'wheat' and 'chaff', I mean 'torrent files' and 'magnet links'
    is_magnet = lambda _: _.startswith("magnet:")
    is_torrent = lambda _: not is_magnet(_)

    # give all the torrents/magnets to the client
    failed = False
    for uploadable in args.torrents:
        try:
            if type(uploadable) is str:
                uploadable = uploadable.decode(sys.stdout.encoding)
            if is_magnet(uploadable):
                client.upload_magnet_link(uploadable)
                util.report_message("%s submitted to seedbox" % uploadable)
            elif is_torrent(uploadable):
                client.upload_torrent(uploadable)
                util.report_message("%s submitted to seedbox" % os.path.basename(uploadable))
            else:
                raise ValueError("%s is not a torrent or a magnet link" % uploadable)
        except Exception as e:
            if args.debug:
                raise
            extramessage = ""
            if isinstance(e, ConnectionError):
                if e.args[0].errno == -2:
                    extramessage = "\nCheck the hostname in your seedboxtools configuration."
            util.report_error("error while uploading %s: %s%s" % (uploadable, e, extramessage))
            failed = True

    if failed:
        return 4
    else:
        return 0
