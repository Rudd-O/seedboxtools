#!/usr/bin/env python

from functools import partial
import seedboxtools.util as util
import re
import os

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
            torrentinfo_path,
        ):
        SeedboxClient.__init__(self,local_download_dir)
        self.hostname = hostname
        self.base_dir = base_dir
        self.incoming_dir = incoming_dir
        self.fluxcli_path = fluxcli_path
        self.torrentinfo_path = torrentinfo_path
        self.getssh = partial(util.ssh_getstdout,hostname=hostname)
        self.passthru = partial(util.ssh_passthru,hostname=hostname)

    def get_finished_torrents(self):
        stdout = self.getssh([self.fluxcli,"transfers"])
        stdout = stdout.splitlines()[2:-5]
        stdout.reverse()
        stdout = [ re.match("^- (.+) - [0123456789\.]+ [KMG]B - (Seeding|Done)",line) for line in stdout ]
        pairs = [ ( match.group(1), match.group(2) ) for match in stdout if match ]
        return pairs

    def get_file_name(self,torrentname):
        fullpath = os.path.join(self.base_dir,".transfers",torrentname)
        stdout = getssh(["LANG=C",self.torrentinfo_path,fullpath).splitlines()
        filenames = [ l[22:] for l in stdout if l.startswith("file name...........: ") ]
        if not len(filenames):
                filelistheader = stdout.index("files...............:")
                # we disregard the actual filenames, we now want the dir name
                #filenames = [ l[3:] for l in stdout[filelistheader+1:] if l.startswith("   ") ]
                filenames = [ l[22:] for l in stdout if l.startswith("directory name......: ") ]
        assert len(filenames) is 1
        return filenames[0]

    def transfer(self,filename):
        # need to single-quote the *path* for the purposes of the remote shell so it doesn't fail, because the path is used in the remote shell
        path = os.path.join(self.incoming_dir,filename)
        path = shell_quote(path)
        path = "%s:%s"%(self.hostname,path)
        opts = ["-arvzP"]
        cmdline = [ "rsync" ] + opts + [ path , local_download_dir ]
        returncode = util.passthru(cmdline)
        return returncode

    def exists_on_server(self,filename):
        path = os.path.join(self.incoming_dir,filename)
        cmd = ["test","-e",path]
        returncode = self.passthru(cmd)
        if returncode == 1: return False
        elif returncode == 0: return True
        elif returncode == -2: raise IOError(4,"exists_on_server interrupted")
        else: raise AssertionError, "exists on server returned %s"%returncode

    def remove_remote_download(filename):
        returncode = self.passthru(["rm","-rf",os.path.join(self.incoming_dir,filename)])
        if returncode == 0: return
        elif returncode == -2: raise IOError(4,"remove_remote_download interrupted")
        else: raise AssertionError, "remove dirs only returned %s"%returncode
