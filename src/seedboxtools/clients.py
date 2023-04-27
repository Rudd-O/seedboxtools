"""
Client classes for seedboxtools
"""

import seedboxtools.util as util
import re
import os
import requests
import json
import subprocess
import xmlrpc.client

from functools import partial
from urllib.parse import quote

# We must present some form of timeout or else the request can hang forever.
# The documentation insists production code must specify it.
def post(*args, **kwargs):
    if "timeout" not in kwargs:
        kwargs = dict(kwargs)
        kwargs["timeout"] = 15
    return requests.post(*args, **kwargs)


def remote_test_minus_e(passthru, path):
    cmd = ["test", "-e", path]
    returncode = passthru(cmd)
    if returncode == 1:
        return False
    elif returncode == 0:
        return True
    elif returncode == -2:
        raise IOError(4, "exists_on_server interrupted")
    else:
        raise subprocess.CalledProcessError(returncode, ["ssh", "<host>"] + cmd)


class SeedboxClientException(Exception):
    pass


class TemporaryMalfunction(SeedboxClientException):
    pass


class Misconfiguration(SeedboxClientException):
    pass


class InvalidTorrent(SeedboxClientException):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "invalid torrent file or magnet link: %r" % self.message


class SeedboxClient:
    def __init__(self, local_download_dir):
        self.local_download_dir = local_download_dir

    def get_finished_torrents(self):
        """
        Returns a series of tuples (torrentdescriptor, "Done")
        for every torrent that is done.
        If there is a temporary error, it raises TemporaryMalfunction.
        """
        raise NotImplementedError

    def get_file_name(self, torrentname):
        """
        Returns the file or path name to the torrent given a
        torrentdescriptor.
        """
        raise NotImplementedError

    def transfer(self, filename):
        raise NotImplementedError

    def exists_on_server(self, filename):
        raise NotImplementedError

    def remove_remote_download(self, filename):
        raise NotImplementedError

    def get_files_to_download(self):
        """Returns iterator with get_finished_torrents result."""
        torrents = self.get_finished_torrents()
        for name, status in torrents:
            yield (name, status, self.get_file_name(name))

    def upload_magnet_link(self, magnet_link):
        raise NotImplementedError

    def upload_torrent(self, torrent_path):
        raise NotImplementedError


class TorrentFluxClient(SeedboxClient):
    def __init__(
        self,
        local_download_dir,
        hostname,
        base_dir,
        incoming_dir,
        torrentinfo_path,
        fluxcli_path,
        ssh_hostname="",
    ):
        SeedboxClient.__init__(self, local_download_dir)
        self.hostname = hostname
        self.ssh_hostname = ssh_hostname or hostname
        self.base_dir = base_dir
        self.incoming_dir = incoming_dir
        self.fluxcli_path = fluxcli_path
        self.torrentinfo_path = torrentinfo_path

        self.getssh = partial(util.ssh_getstdout, self.ssh_hostname)
        self.passthru = partial(util.ssh_passthru, self.ssh_hostname)

    def get_finished_torrents(self):
        stdout = self.getssh([self.fluxcli, "transfers"])
        stdout = stdout.splitlines()[2:-5]
        stdout.reverse()
        stdout = [
            re.match("^- (.+) - [0123456789.]+ [KMG]B - (Seeding|Done)", line)
            for line in stdout
        ]
        pairs = [(match.group(1), match.group(2)) for match in stdout if match]
        return pairs

    def get_file_name(self, torrentname):
        fullpath = os.path.join(self.base_dir, ".transfers", torrentname)
        stdout = self.getssh(
            ["env", "LANG=C", self.torrentinfo_path, fullpath]
        ).splitlines()

        def isf(x):
            return x.startswith("file name...........: ")

        def isd(x):
            return x.startswith("directory name......: ")

        filenames = [f[22:] for f in stdout if isf(f)]
        if not len(filenames):
            _ = stdout.index("files...............:")
            # we disregard the actual filenames, we now want the dir name
            filenames = [f[22:] for f in stdout if isd(f)]
        assert len(filenames) == 1, "Wrong length of filenames: %r" % filenames
        return filenames[0]

    def transfer(self, filename):
        path = os.path.join(self.incoming_dir, filename)
        path = "%s:%s" % (self.ssh_hostname, path)
        return util.rsync(path, self.local_download_dir)

    def exists_on_server(self, filename):
        path = os.path.join(self.incoming_dir, filename)
        return remote_test_minus_e(self.passthru, path)

    def remove_remote_download(self, filename):
        returncode = self.passthru(
            ["rm", "-rf", os.path.join(self.incoming_dir, filename)]
        )
        if returncode == 0:
            return
        elif returncode == -2:
            raise IOError(4, "remove_remote_download interrupted")
        else:
            raise AssertionError("remove dirs only returned %s" % returncode)


class TransmissionClient(SeedboxClient):
    def __init__(
        self,
        local_download_dir,
        hostname,
        torrents_dir,
        incoming_dir,
        torrentinfo_path,
        transmission_remote_path,
        transmission_remote_user,
        transmission_remote_password,
        ssh_hostname="",
    ):
        SeedboxClient.__init__(self, local_download_dir)
        self.hostname = hostname
        self.torrents_dir = torrents_dir
        self.incoming_dir = incoming_dir
        self.transmission_remote_path = transmission_remote_path
        self.transmission_remote_user = transmission_remote_user
        self.transmission_remote_password = transmission_remote_password
        self.ssh_hostname = ssh_hostname or hostname

        self.getssh = partial(util.ssh_getstdout, self.ssh_hostname)
        self.passthru = partial(util.ssh_passthru, self.ssh_hostname)

    def get_finished_torrents(self):
        u, p = (
            self.transmission_remote_user,
            self.transmission_remote_password,
        )
        stdout = util.getstdout(
            [
                self.transmission_remote_path,
                self.hostname,
                f"--auth={u}:{p}",
                "-l",
            ]
        )
        stdout = stdout.splitlines()[1:-1]
        stdout.reverse()
        stdout = [x.split() + [x[70:]] for x in stdout]

        def donetoseeding(t):
            return "Seeding" if t != "Stopped" else t

        stdout = [
            (
                x[0],
                donetoseeding(x[8]),
                x[-1],
            )
            for x in stdout
            if x[4] in "Done"
        ]
        self.torrent_to_id_map = dict((x[2], x[0]) for x in stdout)
        pairs = [(x[2], x[1]) for x in stdout]
        return pairs

    def get_file_name(self, torrentname):
        # first, cache the torrent names to IDs
        if not hasattr(self, "torrent_to_id_map"):
            self.get_finished_torrents()
        torrent_id = self.torrent_to_id_map[torrentname]
        u, p = (
            self.transmission_remote_user,
            self.transmission_remote_password,
        )
        stdout = util.getstdout(
            [
                "env",
                "LANG=C",
                self.transmission_remote_path,
                self.hostname,
                f"--auth={u}:{p}",
                "-t",
                torrent_id,
                "-f",
            ]
        ).splitlines()
        filename = util.firstcomponent(stdout[2][34:])
        return filename

    def transfer(self, filename):
        path = os.path.join(self.incoming_dir, filename)
        path = "%s:%s" % (self.ssh_hostname, path)
        return util.rsync(path, self.local_download_dir)

    def exists_on_server(self, filename):
        path = os.path.join(self.incoming_dir, filename)
        return remote_test_minus_e(self.passthru, path)

    def remove_remote_download(self, filename):
        if not hasattr(self, "torrent_to_id_map"):
            self.get_finished_torrents()
        if not hasattr(self, "filename_to_torrent_map"):
            self.filename_to_torrent_map = dict(
                (self.get_file_name(torrentname), torrentname)
                for torrentname, _ in self.get_finished_torrents()
            )
        torrent = self.filename_to_torrent_map[filename]
        torrent_id = self.torrent_to_id_map[torrent]
        u, p = (
            self.transmission_remote_user,
            self.transmission_remote_password,
        )
        returncode = util.passthru(
            [
                "env",
                "LANG=C",
                self.transmission_remote_path,
                self.hostname,
                f"--auth={u}:{p}",
                "-t",
                torrent_id,
                "--remove-and-delete",
            ]
        )
        if returncode == 0:
            return
        elif returncode == -2:
            raise IOError(4, "remove_remote_download interrupted")
        else:
            raise AssertionError("remove dirs only returned %s" % returncode)


class PulsedMediaClient(SeedboxClient):
    def __init__(
        self,
        local_download_dir,
        hostname,
        login,
        password,
        ssh_hostname="",
        label="",
    ):
        """Client for ruTorrent servers default in PulsedMedia seedboxes."""
        SeedboxClient.__init__(self, local_download_dir)
        self.hostname = hostname
        self.ssh_hostname = ssh_hostname or hostname
        self.login = login
        self.password = password
        self.label = label.strip()

        self.getssh = partial(
            util.ssh_getstdout,
            "%s@%s" % (login, self.ssh_hostname),
        )
        self.passthru = partial(
            util.ssh_passthru,
            "%s@%s" % (login, self.ssh_hostname),
        )

        # Here we disable the certificate warnings that take place with
        # PulsedMedia's less-than-nice SSL certificates.  Tragic, but the
        # alternative is to keep spamming the log forever.
        try:
            import requests.packages.urllib3

            requests.packages.urllib3.disable_warnings()
        except (ImportError, Exception):
            pass

    def get_finished_torrents(self):
        r = post(
            "https://%s/user-%s/rutorrent/plugins/httprpc/action.php"
            % (self.hostname, self.login),
            auth=(self.login, self.password),
            data="mode=list",
        )
        if r.status_code == 500:
            raise TemporaryMalfunction(
                "Server returned a temporary 500 status code: %s" % r.content
            )
        if r.status_code == 404:
            raise Misconfiguration(
                "Server address (%s) may be misconfigured: %s" % self.hostname
            )
        assert r.status_code == 200, (
            "Non-OK status code while retrieving get_finished_torrents: %r"
            % r.status_code
        )
        data = json.loads(r.content)
        torrents = data["t"]
        if not torrents:
            #  There are no torrents to download, or so the server says.
            return []
        self.torrents_cache = torrents
        try:
            self.path_for_filename_cache = dict(
                [
                    (os.path.basename(torrent[25]), torrent[25])
                    for torrent in list(torrents.values())
                ]
            )
            self.hash_for_filename_cache = dict(
                [
                    (os.path.basename(torrent[25]), thehash)
                    for thehash, torrent in list(torrents.items())
                ]
            )
        except AttributeError as e:
            raise AttributeError(
                "normally this would be a 'list' object has no attribute 'values', but in reality something went wrong with the unserialization of JSON values, which were serialized from %r and were supposed to come from the 't' bag of JSON data -- this happens when PulsedMedia's server fucks up (%s)"
                % (r.content, e)
            )
        done_torrents = []
        for key, torrent in list(torrents.items()):
            # filename = torrent[25]
            completed_chunks = int(torrent[6])
            size_chunks = int(torrent[7])
            done = completed_chunks / size_chunks
            if self.label and self.label != torrent[14]:
                # If it does not match the label, the torrent is
                # never "done".
                done = 0
            if done == 1:
                done_torrents.append(
                    (key, "Done" if int(torrent[0]) == 0 else "Seeding")
                )
        return done_torrents

    def get_file_name(self, torrentname):
        # in this implementation, get_finished_torrents MUST BE called first
        # or else this will bomb out with an attribute error
        torrent = self.torrents_cache[torrentname]
        return os.path.basename(torrent[25])

    def transfer(self, filename):
        # in this implementation, get_finished_torrents MUST BE called first
        # or else this will bomb out with an attribute error
        path = self.path_for_filename_cache[filename]
        path = "%s@%s:%s" % (self.login, self.ssh_hostname, path)
        return util.rsync(path, self.local_download_dir)

    def exists_on_server(self, filename):
        # in this implementation, get_finished_torrents MUST BE called first
        # or else this will bomb out with an attribute error
        path = self.path_for_filename_cache[filename]
        return remote_test_minus_e(self.passthru, path)

    def upload_magnet_link(self, magnet_link):
        return self._upload(data={"url": magnet_link})

    def upload_torrent(self, torrent_path):
        n = os.path.basename(torrent_path)
        with open(torrent_path, "rb") as tf:
            return self._upload(files={"torrent_file": (n, tf)})

    def _upload(self, **params):
        r = post(
            "https://%s/user-%s/rutorrent/php/addtorrent.php"
            % (self.hostname, self.login),
            auth=(self.login, self.password),
            **params,
        )
        if r.status_code == 500:
            raise TemporaryMalfunction(
                "Server returned a temporary 500 status code: %s" % r.text
            )
        if r.status_code == 404:
            raise Misconfiguration(
                "Server address (%s) may be misconfigured: %s"
                % (self.hostname, r.status_code)
            )

        if "addTorrentSuccess" in r.text:
            return

        if "addTorrentFailed" in r.text:
            if "data" in params:
                raise InvalidTorrent(params["data"]["url"])
            raise InvalidTorrent(params["files"]["torrent_file"][0])

        assert 0, (r.status_code, r.text)

    def remove_remote_download(self, filename):
        # in this implementation, get_finished_torrents MUST BE called first
        # or else this will bomb out with an attribute error
        login = quote(self.login, safe="")
        passw = quote(self.password, safe="")
        url = (
            f"https://{login}:{passw}@{self.hostname}/user-{login}"
            + "/rutorrent/plugins/httprpc/action.php"
        )
        client = xmlrpc.client.ServerProxy(url)
        infohash = self.hash_for_filename_cache[filename]
        mcall = xmlrpc.client.MultiCall(client)
        mcall.d.custom5.set(infohash, "1")
        mcall.d.delete_tied(infohash)
        mcall.d.erase(infohash)
        try:
            _, delete_tied_result, erase_result = list(mcall())
        except xmlrpc.client.ProtocolError as exc:
            raise Misconfiguration(
                f"Server address ({self.hostname}) may be misconfigured"
            ) from exc
        except xmlrpc.client.Fault as exc:
            raise TemporaryMalfunction("Server returned a fault.") from exc

        assert delete_tied_result == 0, f"Delete tied result {delete_tied_result}"
        assert erase_result == 0, f"Erase result {erase_result}"


clients = {
    "TransmissionClient": TransmissionClient,
    "TorrentFluxClient": TorrentFluxClient,
    "PulsedMedia": PulsedMediaClient,
}


def lookup_client(name):
    return clients[name]
