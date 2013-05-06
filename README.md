Seedbox tools (seedboxtools)
============================

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

Tools included in this set
--------------------------

This package contains several tools:
    
    1. leechtorrents: a tool that leeches finished downloads from a torrent
       seedbox to your local computer.
    2. configleecher: a configuration wizard to set up the clients to work
       properly against your seedbox.
    3. uploadtorrents: a tool that lets you queue up a torrent or magnet link
       for download on your seedbox.

What you need to have before using this package
-----------------------------------------------
    
    - Python 2.7 on your local machine
    - Python iniparse installed there
    - Python requests installed there, version 0.11.1 or higher (with SSL support)
    - a seedbox running TorrentFlux-b4rt or Transmission Web + API, or
      a PulsedMedia ruTorrent seedbox from PulsedMedia.com
    - an SSH server on your seedbox
    - an SSH client on your local machine
    - a public key-authenticated user account in the seedbox, so that your user
      can log in without passwords and can read the torrents and downloads
      directories in the seedbox
    - rsync installed on both machines
    - if you are using TorrentFlux-b4rt on your seedbox:
        * the command torrentinfo-console from the BitTorrent package, installed
          on the seedbox
        * the command fluxcli installed and operational on the seedbox
    - if you are using Transmission on your seedbox:
        * the command transmission-remote from the Transmission package,
          installed on your local machine
        * the API server port open so that transmission-remote can query it
    - if you are using a PulsedMedia seedbox, you don't need to do anything

Installation
------------

You will need to install this package on your local machine.

You can install this package directly from PyPI using pip::

    pip install seedboxtools

If you are on an RPM-based distribution, build an RPM from the source package
and install the resulting RPM::
    
    python setup.py bdist_rpm

Otherwise, just use the standard Python installation system::

    python setup.py install

You can also run it directly from the unpacked source directory::
    
    export PYTHONPATH=src
    bin/leechtorrents --help

Configuration
-------------

The tools require some configuration after installation.  There is a nifty
configuration wizard that will set the configuration file up.  Run it and
answer a few questions::
    
    configleecher

The script will ask you for the necessary configuration values before you can
run the tools here.  You should run this wizard on the machine where you'll
be running `leechtorrents` (see below).

Note: Both TorrentFlux and Transmission protect their download and torrent
directories using permissions.  You should become part of the UNIX group
they use to protect those directories, and change the permissions
accordingly so you have at least read and list permissions (rx).
    
Downloading finished torrents with the leecher tool
---------------------------------------------------

The leecher tool will contact your seedbox and ask for a listing of finished
torrents, then download them locally to the directory you chose during
configuration.  There are various ways to run the script:

* manually on a terminal window
* with cron
* in a systemd unit file as a service

Manually
________

In your terminal program of choice, just run the command::

    leechtorrents

There are various options you can supply to the program to change its
behavior, such as enabling periodic checks and logging to a file. Run
`leechtorrents -h` to see the options.

With cron
~~~~~~~~~

Put this in your crontab to run it every minute::

    * * * * * leechtorrents -Dql

`leechtorrents` will daemonize itself, write to its default log file (which
you could change with another command line option), and be quiet if no work
needs to be done.  Locking prevents multiple `leechtorrents` processes from
running simultaneously.

With systemd
~~~~~~~~~~~~

Create a unit file::

    # Listing: /etc/systemd/system/leechtorrents.service
    # ====================================================

    [Unit]
    Description=Torrentleecher
    After=network.target
    
    [Service]
    Type=simple
    ExecStart=/usr/bin/leechtorrents -g .torrentleecher.log -ql -t 30
    User=<YOUR_USERNAME_GOES_HERE>
    Restart=always
    
    [Install]
    WantedBy=network.target

Then run as root::

    systemctl daemon-reload
    systemctl enable leechtorrents.service
    systemctl start leechtorrents.service

How to upload torrents to your seedbox
--------------------------------------

The `uploadtorrents` command-line tool included in this package will upload the
provided torrent files or magnet links to your seedbox::

    uploadtorrents TORRENT [TORRENT ...]

This tool currently only supports PulsedMedia clients.
