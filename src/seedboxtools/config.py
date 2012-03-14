'''
Configuration for the seedbox downloader
'''

import os
from iniparse import INIConfig
from seedboxtools import clients

default_filename = os.path.expanduser("~/.torrentleecher.cfg")

def get_default_config():
    cfg = INIConfig()
    cfg.general.client = 'TransmissionClient'
    cfg.general.local_download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    cfg[cfg.general.client].hostname = ''
    cfg[cfg.general.client].torrents_dir = '/var/lib/transmission/torrents'
    cfg[cfg.general.client].incoming_dir = '/var/lib/transmission/Downloads'
    cfg[cfg.general.client].transmission_remote_path = 'transmission-remote'
    cfg[cfg.general.client].transmission_remote_user = 'admin'
    cfg[cfg.general.client].transmission_remote_password = ''
    cfg[cfg.general.client].torrentinfo_path = 'torrentinfo-console'
    return cfg

def load_config(fobject):
    cfg = INIConfig(fobject)
    return cfg

def save_config(cfgobject, fobject):
    text = str(cfgobject)
    fobject.write(text)
    fobject.flush()

def get_client(config):
    client_constructor = clients.lookup_client(config.general.client)
    args = {"local_download_dir":config.general.local_download_dir}
    client_props = getattr(config, config.general.client)
    args.update(set([ (x, getattr(client_props, x)) for x in client_props ]))
    args = dict(args)
    return client_constructor(**args)

def raw_input_default(prompt, default, choices=None):
    if choices:
        choices_str = " or ".join(choices) + ", default "
    else:
        choices_str = ''
    string = prompt + " (%s%s): " % (choices_str, default)
    _ = raw_input(string)
    choice = _ if _ else default
    if choices and choice not in choices:
        print choice, "is not in the choices, please try again"
        return raw_input_default(prompt, default, choices)
    return choice

def wizard():
    cfg = get_default_config()
    try:
        f = open(default_filename)
        cfg = load_config(f)
    except (IOError, OSError):
        print "Couldn't load configuration.  Creating a new configuration file."
    cfg.general.local_download_dir = raw_input_default(
          "Local download directory",
          cfg.general.local_download_dir,
    )
    cfg.general.client = raw_input_default(
          "Torrent server type",
          cfg.general.client,
          ["TorrentFluxClient", "TransmissionClient"],
    )
    if cfg.general.client == 'TransmissionClient':
        cfg[cfg.general.client].hostname = raw_input_default(
              "Torrent server host name",
              cfg[cfg.general.client].hostname,
        )
        cfg[cfg.general.client].torrents_dir = raw_input_default(
              "Directory where the torrent server stores torrent files",
              cfg[cfg.general.client].torrents_dir,
        )
        cfg[cfg.general.client].incoming_dir = raw_input_default(
              "Directory where the torrent server stores downloaded files",
              cfg[cfg.general.client].incoming_dir,
        )
        cfg[cfg.general.client].transmission_remote_path = raw_input_default(
              "Command to run transmission-remote locally",
              cfg[cfg.general.client].transmission_remote_path,
        )
        cfg[cfg.general.client].transmission_remote_user = raw_input_default(
              "User name for transmission-remote",
              cfg[cfg.general.client].transmission_remote_user,
        )
        cfg[cfg.general.client].transmission_remote_password = raw_input_default(
              "Password for transmission-remote",
              cfg[cfg.general.client].transmission_remote_password,
        )
        cfg[cfg.general.client].torrentinfo_path = raw_input_default(
              "Command to run torrentinfo-console in the server",
              cfg[cfg.general.client].torrentinfo_path,
        )
    elif cfg.general.client == 'TorrentFluxClient':
        cfg[cfg.general.client].hostname = raw_input_default(
              "Torrent server host name",
              cfg[cfg.general.client].hostname,
        )
        cfg[cfg.general.client].base_dir = raw_input_default(
              "Base directory where TorrentFlux stores its .transfers directory",
              cfg[cfg.general.client].base_dir,
        )
        cfg[cfg.general.client].incoming_dir = raw_input_default(
              "Directory where where TorrentFlux stores downloaded files",
              cfg[cfg.general.client].incoming_dir,
        )
        cfg[cfg.general.client].fluxcli_path = raw_input_default(
              "Command to run fluxcli in the server",
              cfg[cfg.general.client].fluxcli_path,
        )
        cfg[cfg.general.client].torrentinfo_path = raw_input_default(
              "Command to run torrentinfo-console in the server",
              cfg[cfg.general.client].torrentinfo_path,
        )
    else:
        assert 0, "Not reached"
    print "Writing this configuration to %s" % default_filename
    print "===============8<================"
    print cfg
    print "===============>8================"
    oldumask = os.umask(0077)
    save_config(cfg, open(default_filename, "w"))
    os.umask(oldumask)
    print "Done.  You are ready to run leechtorrents."

