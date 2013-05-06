'''
Client classes for seedboxtools
'''

from functools import partial
import seedboxtools.util as util
import re
import os
import requests
import json

class SeedboxClientException(Exception): pass

class TemporaryMalfunction(SeedboxClientException): pass

class InvalidTorrent(SeedboxClientException):
    def __str__(self):
        return "invalid torrent file or magnet link: %r" % self.message

class SeedboxClient:

    def __init__(self, local_download_dir):
        self.local_download_dir = local_download_dir

    def get_finished_torrents(self):
        # This returns a series of tuples (torrentdescriptor, "Done") for every torrent that is done
        # If there is a temporary error, it raises TemporaryMalfunction
        raise NotImplementedError

    def get_file_name(self, torrentname):
        # This returns the file or path name to the torrent given a torrentdescriptor
        raise NotImplementedError

    def transfer(self, filename):
        raise NotImplementedError

    def exists_on_server(self, filename):
        raise NotImplementedError

    def remove_remote_download(self, filename):
        raise NotImplementedError

    def get_files_to_download(self):
        """Returns iterator with get_finished_torrents result"""
        torrents = self.get_finished_torrents()
        for name, status in torrents:
            yield (name, status, self.get_file_name(name))

    def upload_magnet_link(self, magnet_link):
        raise NotImplementedError

    def upload_torrent(self, torrent_path):
        raise NotImplementedError


class TorrentFluxClient(SeedboxClient):
    def __init__(self,
            local_download_dir,
            hostname,
            base_dir,
            incoming_dir,
            torrentinfo_path,
            fluxcli_path,
        ):
        SeedboxClient.__init__(self, local_download_dir)
        self.hostname = hostname
        self.base_dir = base_dir
        self.incoming_dir = incoming_dir
        self.fluxcli_path = fluxcli_path
        self.torrentinfo_path = torrentinfo_path

        self.getssh = partial(util.ssh_getstdout, hostname)
        self.passthru = partial(util.ssh_passthru, hostname)

    def get_finished_torrents(self):
        stdout = self.getssh([self.fluxcli, "transfers"])
        stdout = stdout.splitlines()[2:-5]
        stdout.reverse()
        stdout = [ re.match("^- (.+) - [0123456789\.]+ [KMG]B - (Seeding|Done)", line) for line in stdout ]
        pairs = [ (match.group(1), match.group(2)) for match in stdout if match ]
        return pairs

    def get_file_name(self, torrentname):
        fullpath = os.path.join(self.base_dir, ".transfers", torrentname)
        stdout = self.getssh(["env", "LANG=C", self.torrentinfo_path, fullpath]).splitlines()
        filenames = [ l[22:] for l in stdout if l.startswith("file name...........: ") ]
        if not len(filenames):
                _ = stdout.index("files...............:")
                # we disregard the actual filenames, we now want the dir name
                #filenames = [ l[3:] for l in stdout[filelistheader+1:] if l.startswith("   ") ]
                filenames = [ l[22:] for l in stdout if l.startswith("directory name......: ") ]
        assert len(filenames) is 1, "Wrong length of filenames: %r"%filenames
        return filenames[0]

    def transfer(self, filename):
        # need to single-quote the *path* for the purposes of the remote shell so it doesn't fail, because the path is used in the remote shell
        path = os.path.join(self.incoming_dir, filename)
        path = util.shell_quote(path)
        path = "%s:%s" % (self.hostname, path)
        opts = ["-arvzP"]
        cmdline = [ "rsync" ] + opts + [ path , self.local_download_dir ]
        returncode = util.passthru(cmdline)
        return returncode

    def exists_on_server(self, filename):
        path = os.path.join(self.incoming_dir, filename)
        cmd = ["test", "-e", path]
        returncode = self.passthru(cmd)
        if returncode == 1: return False
        elif returncode == 0: return True
        elif returncode == -2: raise IOError(4, "exists_on_server interrupted")
        else: raise AssertionError, "exists on server returned %s" % returncode

    def remove_remote_download(self, filename):
        returncode = self.passthru(["rm", "-rf", os.path.join(self.incoming_dir, filename)])
        if returncode == 0: return
        elif returncode == -2: raise IOError(4, "remove_remote_download interrupted")
        else: raise AssertionError, "remove dirs only returned %s" % returncode


class TransmissionClient(SeedboxClient):
    def __init__(self,
            local_download_dir,
            hostname,
            torrents_dir,
            incoming_dir,
            torrentinfo_path,
            transmission_remote_path,
            transmission_remote_user,
            transmission_remote_password,
        ):
        SeedboxClient.__init__(self, local_download_dir)
        self.hostname = hostname
        self.torrents_dir = torrents_dir
        self.incoming_dir = incoming_dir
        self.transmission_remote_path = transmission_remote_path
        self.transmission_remote_user = transmission_remote_user
        self.transmission_remote_password = transmission_remote_password

        self.getssh = partial(util.ssh_getstdout, hostname)
        self.passthru = partial(util.ssh_passthru, hostname)

    def get_finished_torrents(self):
        stdout = util.getstdout([
            self.transmission_remote_path,
            self.hostname,
            "--auth=%s:%s" % (self.transmission_remote_user, self.transmission_remote_password),
            "-l"
        ])
        stdout = stdout.splitlines()[1:-1]
        stdout.reverse()
        stdout = [ x.split() + [x[70:]] for x in stdout ]
        donetoseeding = lambda t: "Seeding" if t != "Stopped" else t
        stdout = [ (x[0], donetoseeding(x[8]), x[-1]) for x in stdout if x[4] in "Done" ]
        self.torrent_to_id_map = dict((x[2], x[0]) for x in stdout)
        pairs = [ (x[2], x[1]) for x in stdout]
        return pairs

    def get_file_name(self, torrentname):
        # first, cache the torrent names to IDs
        if not hasattr(self, "torrent_to_id_map"): self.get_finished_torrents()
        torrent_id = self.torrent_to_id_map[torrentname]
        stdout = util.getstdout([
            "env", "LANG=C",
            self.transmission_remote_path,
            self.hostname,
            "--auth=%s:%s" % (self.transmission_remote_user, self.transmission_remote_password),
            "-t", torrent_id,
            "-f"
        ]).splitlines()
        filename = util.firstcomponent(stdout[2][34:])
        return filename

    def transfer(self, filename):
        # need to single-quote the *path* for the purposes of the remote shell so it doesn't fail, because the path is used in the remote shell
        path = os.path.join(self.incoming_dir, filename)
        path = util.shell_quote(path)
        path = "%s:%s" % (self.hostname, path)
        opts = ["-arvzP"]
        cmdline = [ "rsync" ] + opts + [ path , self.local_download_dir ]
        returncode = util.passthru(cmdline)
        return returncode

    def exists_on_server(self, filename):
        path = os.path.join(self.incoming_dir, filename)
        cmd = ["test", "-e", path]
        returncode = self.passthru(cmd)
        if returncode == 1: return False
        elif returncode == 0: return True
        elif returncode == -2: raise IOError(4, "exists_on_server interrupted")
        else: raise AssertionError, "exists on server returned %s" % returncode

    def remove_remote_download(self, filename):
        if not hasattr(self, "torrent_to_id_map"): self.get_finished_torrents()
        if not hasattr(self, "filename_to_torrent_map"):
            self.filename_to_torrent_map = dict(
                (self.get_file_name(torrentname), torrentname) for torrentname, _ in self.get_finished_torrents()
            )
        torrent = self.filename_to_torrent_map[filename]
        torrent_id = self.torrent_to_id_map[torrent]
        returncode = util.passthru([
            "env", "LANG=C",
            self.transmission_remote_path,
            self.hostname,
            "--auth=%s:%s" % (self.transmission_remote_user, self.transmission_remote_password),
            "-t", torrent_id,
            "--remove-and-delete"
        ])
        if returncode == 0: return
        elif returncode == -2: raise IOError(4, "remove_remote_download interrupted")
        else: raise AssertionError, "remove dirs only returned %s" % returncode


class PulsedMediaClient(SeedboxClient):
    def __init__(self,
            local_download_dir,
            hostname,
            login,
            password,
        ):
        SeedboxClient.__init__(self, local_download_dir)
        self.hostname = hostname
        self.login = login
        self.password = password

        self.getssh = partial(util.ssh_getstdout, hostname)
        self.passthru = partial(util.ssh_passthru, hostname)

    def get_finished_torrents(self):
	r = requests.post(
		"https://%s/rutorrent/plugins/httprpc/action.php"%self.hostname,
		auth=(self.login, self.password),
		data="mode=list",
		verify=False,
	)
	if r.status_code == 500:
		raise TemporaryMalfunction(
			"Server is experiencing a temporary 500 status code: %s"%\
			r.content
		)
	assert r.status_code == 200, "Non-OK status code while retrieving get_finished_torrents: %r"%r.status_code
	data = json.loads(r.content)
	torrents = data["t"]
	self.torrents_cache = torrents
	try:
		self.path_for_filename_cache = dict([
			(os.path.basename(torrent[25]), torrent[25])
			for torrent in torrents.values()
		])
	except AttributeError, e:
		raise AttributeError, "normally this would be a 'list' object has no attribute 'values', but in reality something went wrong with the unserialization of JSON values, which were serialized from %r and were supposed to come from the 't' bag of JSON data -- this happens when PulsedMedia's server fucks up"%r.content
	done_torrents = []
	for key,torrent in torrents.items():
		#filename = torrent[25]
		completed_chunks = int(torrent[6])
		size_chunks = int(torrent[7])
		done = completed_chunks/size_chunks
		if done == 1: done_torrents.append( (key, "Done") )
        return done_torrents

    def get_file_name(self, torrentname):
	# in this implementation, get_finished_torrents MUST BE called first
	# or else this will bomb out with an attribute error
	torrent = self.torrents_cache[torrentname]
	return os.path.basename(torrent[25])

    def transfer(self, filename):
        # in this implementation, get_finished_torrents MUST BE called first
        # or else this will bomb out with an attribute error
        # need to single-quote the *path* for the purposes of the remote shell so it doesn't fail, because the path is used in the remote shell
        path = util.shell_quote(self.path_for_filename_cache[filename])
        path = "%s:%s" % (self.hostname, path)
        opts = ["-arvzP"]
        cmdline = [ "rsync" ] + opts + [ path , self.local_download_dir ]
        returncode = util.passthru(cmdline)
        return returncode

    def exists_on_server(self, filename):
        # in this implementation, get_finished_torrents MUST BE called first
        # or else this will bomb out with an attribute error
        path = self.path_for_filename_cache[filename]
        cmd = ["test", "-e", path] # the self.passthru takes care of quoting
        returncode = self.passthru(cmd)
        if returncode == 1: return False
        elif returncode == 0: return True
        elif returncode == -2: raise IOError(4, "exists_on_server interrupted")
        else: raise AssertionError, "exists on server returned %s" % returncode

    def upload_magnet_link(self, magnet_link):
        return self._upload(data={'url': magnet_link})

    def upload_torrent(self, torrent_path):
        files={'torrent_file': (os.path.basename(torrent_path),
                                open(torrent_path, 'rb')) }
        return self._upload(files=files)

    def _upload(self, **params):
        r = requests.post(
            "https://%s/rutorrent/php/addtorrent.php"%self.hostname,
            auth=(self.login, self.password),
            verify=False,
            **params
        )
        if r.status_code == 500:
            raise TemporaryMalfunction(
                "Server is experiencing a temporary 500 status code: %s"%\
                r.content
            )
        if 'addTorrentSuccess' in r.content:
            return
        elif 'addTorrentFailed' in r.content:
            raise InvalidTorrent(magnet_link)
        else:
            assert 0, (r.status_code, r.content)


clients = {
    'TransmissionClient':TransmissionClient,
    'TorrentFluxClient':TorrentFluxClient,
    'PulsedMedia':PulsedMediaClient,
}

def lookup_client(name):
    return clients[name]
