#!/usr/bin/env python

from functools import partial
import seedboxtools.util as util
import re

class SeedboxClient:

    def __init__(self
            local_download_dir):
        self.local_download_dir = local_download_dir

    def get_finished_torrents():
        raise NotImplementedError


class TorrentFluxClient(SeedboxClient):
    def __init__(self,
            local_download_dir,
            hostname,
            base_dir,
            incoming_dir,
            fluxcli_path,
        ):
        SeedboxClient.__init__(self,local_download_dir)
        self.hostname = hostname
        self.base_dir = base_dir
        self.incoming_dir = incoming_dir
        self.fluxcli_path = fluxcli_path
        self.getssh = partial(util.ssh_getstdout,hostname=hostname)

    def get_finished_torrents(self):
        stdout = self.getssh([self.fluxcli,"transfers"])
        stdout = stdout.splitlines()[2:-5]
        stdout.reverse()
        stdout = [ re.match("^- (.+) - [0123456789\.]+ [KMG]B - (Seeding|Done)",line) for line in stdout ]
        pairs = [ ( match.group(1), match.group(2) ) for match in stdout if match ]
        return pairs
