'''
This is the code in charge of downloading proper
'''

import os
from seedboxtools import util

# start execution here
def download(client, remove_finished=False):
    for torrent, status, filename in client.get_files_to_download():
        # Set loop vars up
        download_lockfile = ".%s.done" % filename
        fully_downloaded = os.path.exists(download_lockfile)
        seeding = status == "Seeding"

        # If the file is completely downloaded but not to be remotely removed, skip
        if fully_downloaded and not remove_finished:
            util.report_message("%s from %s is fully downloaded, continuing to next torrent" % (filename, torrent))
            continue

        # If the remote files don't exist, skip
        util.report_message("Checking if %s from torrent %s exists on server" % (filename, torrent))
        if not client.exists_on_server(filename):
            util.report_message("%s from %s is no longer available on server, continuing to next torrent" % (filename, torrent))
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
                    util.report_error("Download of %s stopped -- rsync process interrupted" % (filename,))
                    util.report_message("Finishing by user request")
                    return 2
                elif retvalue < 0:
                    util.report_error("Download of %s failed -- rsync process killed with signal %s" % (filename, -retvalue))
                    util.report_message("Aborting")
                    return 1
                else:
                    util.report_error("Download of %s failed -- rsync process exited with return status %s" % (filename, retvalue))
                    util.report_message("Aborting")
                    return 1
            # Rsync successful
            # mark file as downloaded
            try: file(download_lockfile, "w").write("Done")
            except OSError, e:
                if e.errno != 17: raise
            # report successful download
            fully_downloaded = True
            util.mark_dir_complete(filename)
            util.report_message("Download of %s complete" % filename)

        else:

            if remove_finished:
                if seeding:
                    util.report_message("%s from %s is complete but still seeding, not removing" % (filename, torrent))
                else:
                    client.remove_remote_download(filename)
                    util.report_message("Removal of %s complete" % filename)

