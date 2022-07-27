# Seedbox tools (seedboxtools)

| Donate to support this free software |
|:------------------------------------:|
| <img width="164" height="164" title="" alt="" src="doc/bitcoin.png" /> |
| [12cXnYY3wabbPmLpS7ZgACh4mBawrXdndk](bitcoin:12cXnYY3wabbPmLpS7ZgACh4mBawrXdndk) |

The seedbox tools will help you download all those Linux ISOs that you
downloaded on your remote seedbox (whether it's a Transmission Web, or
TorrentFlux-b4rt, or a PulsedMedia seedbox) 100% automatically, without any
manual intervention on your part.

With this program installed on your home computer, all you need to do is
simply start a torrent in your seedbox, from anywhere you are; then, when
you get back home, all your downloads will be fully downloaded at home,
ready to use and enjoy.

## Tools included in this set

This package contains several tools:
    
1. leechtorrents: a tool that leeches finished downloads from a torrent
   seedbox to your local computer.
2. configleecher: a configuration wizard to set up the clients to work
   properly against your seedbox.
3. uploadtorrents: a tool that lets you queue up a torrent or magnet link
   for download on your seedbox.

## What you need to have before using this package
    
* Python 3.7 on your local machine
* Python iniparse installed there
* Python requests installed there, version 0.11.1 or higher (with SSL support)
* a seedbox running TorrentFlux-b4rt or Transmission Web + API, or
  a PulsedMedia ruTorrent seedbox from PulsedMedia.com
* an SSH server on your seedbox
  * an SSH client on your local machine
  * a public key-authenticated user account in the seedbox, so that your user
    can log in without passwords and can read the torrents and downloads
    directories in the seedbox
  * rsync installed on both machines
  * if you are using TorrentFlux-b4rt on your seedbox:
    * the command torrentinfo-console from the BitTorrent package, installed
      on the seedbox
    * the command fluxcli installed and operational on the seedbox
  * if you are using Transmission on your seedbox:
    * the command transmission-remote from the Transmission package,
      installed on your local machine
    * the API server port open so that transmission-remote can query it
  * if you are using a PulsedMedia seedbox, you don't need to do anything

## Installation

You will need to install this package on your local machine.

You can install this package directly from PyPI using pip::

```
pip install seedboxtools
```

If you are on an RPM-based distribution, build an RPM from the source package
and install the resulting RPM::
    
```
make rpm
```

Otherwise, just use the standard Python installation system::

```
python -m build -s
pip install dist/*.tar.gz
```

You can also run it directly from the unpacked source directory::

```
export PYTHONPATH=src
bin/leechtorrents --help
```

## Configuration

The tools require some configuration after installation.  There is a nifty
configuration wizard that will set the configuration file up.  Run it and
answer a few questions::

```
configleecher
```

The script will ask you for the necessary configuration values before you can
run the tools here.  You should run this wizard on the machine where you'll
be running `leechtorrents` (see below).

Note: Both TorrentFlux and Transmission protect their download and torrent
directories using permissions.  You should become part of the UNIX group
they use to protect those directories, and change the permissions
accordingly so you have at least read and list permissions (rx).
    
## Downloading finished torrents with the leecher tool

The leecher tool will contact your seedbox and ask for a listing of finished
torrents, then download them locally to the directory you chose during
configuration.  There are various ways to run the script:

* manually on a terminal window
* with cron
* in a systemd unit file as a service

In all cases, the leecher tool will figure out finished torrents, download
them to the download folder you configured during the `configleecher` stage,
then create a file named `.<downloaded file>.done` within the download folder,
to indicate that the torrent has finished downloading.  This marker helps the
leecher tool remember which torrents were fully downloaded, so that it doesn't
attempt to download them yet again.

### Manually

In your terminal program of choice, just run the command::

```
leechtorrents
```

There are various options you can supply to the program to change its
behavior, such as enabling periodic checks and logging to a file. Run
`leechtorrents -h` to see the options.

### With cron

Put this in your crontab to run it every minute::

```
* * * * * leechtorrents -Dql
```

`leechtorrents` will daemonize itself, write to its default log file (which
you could change with another command line option), and be quiet if no work
needs to be done.  Locking prevents multiple `leechtorrents` processes from
running simultaneously.

### With systemd

Enable the respective unit file for your user:

```
# $USER contains the user that will run leechtorrents.
# Only run this after configuring the torrent leecher!
sudo systemctl enable --now leechtorrents@$USER
```

You can configure command line options in `/etc/default/leechtorrents` as well
as with `~/.config/leechtorrents-environment`.  The environment variable
`$LEECHTORRENTS_OPTS` is defined in either of those files, and carries the
command-line options that will be used by the program.

You can verify if there are any errors using:

```
sudo systemctl status leechtorrents@$USER
# and
sudo journalctl -b -u leechtorrents@$USER
```

# Removing completed torrents once they have been fully downloaded

The leecher tool has the ability to remove completed downloads that aren't
seeding from your seedbox.  Just pass the command line option `-r` to the
leecher tool `leechtorrents`, and it will automatically remove from the
seedbox each torrent it successfully downloads, so long as the torrent
is not seeding anymore.  This feature helps conserve disk space in your
seedbox.  Note that, once a torrent has been removed from the seedbox,
its corresponding `.<downloaded file>.done` file on the download folder
will be eliminated, to clear up clutter in the download folder.

Example::

```
leechtorrents -r
```

# Running a program after a torrent is finished downloading

The leecher tool has the capacity to run a program (non-interactively) right
after a download is completed, and will also pass the full path to the file
or directory that was downloaded to the program.  This program will be run
right after the download is done, and (if you have enabled said option)
before the torrent is removed from the seedbox, and its marker file removed
from the download folder.

To activate the running of the post-download program, pass the option `-s`
followed by the path to the program you want to run.

Here is an example that runs a particular program to process downloads::

```
leechtorrents -s /usr/local/bin/blend-linux-distributions
```

In this example, right after your favorite Linux distribution torrent
(which surely is `Fedora-22.iso`) is done and saved to your download folder
`/srv/seedbox`, `leechtorrents` will execute the following command line::

```
/usr/local/bin/blend-linux-distributions /srv/seedbox/Fedora-22.iso
```

The standard output and standard error of the program are passed to the
standard output and standard error of `leechtorrents`, which may be your
terminal, a logging service, or the log file set aside for logging purposes
by the `leechtorrents` command line parameter `-l`.  Standard input will
be nullified, so no option for interacting with the program will exist.

Note that your program will only ever execute once per downloaded torrent.
Also note that the return value of your program will be ignored.  Finally,
please note that if your program doesn't finish, this will block further
downloads, so make sure to equip your program with a timeout (perhaps using
`SIGALRM` or such mechanisms).

If you want to run a shell or other language script against the downloaded
file or directory, you are advised to write a script file and pass that as
the argument to `-s`, then use the first argument to the script file as
the path to the downloaded file (it's usually `$1` in sh-like languages,
like it is `sys.argv[1]` in Python).

How to upload torrents to your seedbox
--------------------------------------

The `uploadtorrents` command-line tool included in this package will upload the
provided torrent files or magnet links to your seedbox::

```
uploadtorrents TORRENT [TORRENT ...]
```

This tool currently only supports PulsedMedia clients.
