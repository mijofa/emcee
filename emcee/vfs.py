# This is intended as a wrapper between Emcee and whatever backing store is used behind it.
# For now however, it just returns the lists I want for testing, I'll implement the actual backing store later

import os
import random
import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib
import collections
import configparser

TVDIR = '/srv/share/tv'


with open('epgs', 'r') as f:
    epg_samples = [l.strip() for l in f.readlines()]


# FIXME: Named tuples were a quick-and-dirty way to do this, create proper classes for these objects
Station = collections.namedtuple('Station', 'title icon channels')
ChannelTuple = collections.namedtuple('Channel', 'title icon uri')


class Channel(ChannelTuple):
    def get_epg(self, template="<big>{title}</big>\n<b>NOW</b>: {now_title}\n<b>NEXT\u00A0({next_starttime})</b>: {next_title}"):
        # FIXME: Is this the right place to be doing this escaping?
        return template.format(
            title=self.title.replace(' ', '\u00A0'),  # Use non-breaking space to force this line not to wrap
            now_title=GLib.markup_escape_text(random.choice(epg_samples)),
            next_title=GLib.markup_escape_text(random.choice(epg_samples)),
            next_starttime=GLib.markup_escape_text("23:59\u00A0AM"),
        )


class VirtualFilesystem():
    def list_stations(self):
        stations = []
        ind = 0
        for root, dirs, files in os.walk(TVDIR):
            assert root.startswith(TVDIR)
            root = root[len(TVDIR):].strip('/')  # Remove the TVDIR prefix
            assert '/' not in root

            # Don't traverse hidden directories
            for d in dirs:
                if d.startswith('.'):
                    dirs.remove(d)

            if not root:
                # This is the TVDIR itself
                continue

            # Create the station definition
            st = Station(
                title=root,
                icon=os.path.join(TVDIR, root, 'folder.gif') if 'folder.gif' in files else None,
                channels=[],  # Updated below
            )
            stations.append(st)

            # Create the channel definitions
            for ch in files:
                if not ch.endswith('.info'):
                    # Not a channel definition file
                    continue

                cfg = configparser.ConfigParser()
                cfg.read(os.path.join(TVDIR, root, ch))
                title = ch[:-5]  # Remove the '.info'
                st.channels.append(Channel(
                    title=ch[:-5],  # Remove the '.info'
                    icon=os.path.join(TVDIR, root, title + '.gif') if title + '.gif' in files else None,
                    uri=cfg.get('local', 'filename'),
                ))
                ind += 2

        return stations

if __name__ == '__main__':
    import pprint
    pprint.pprint(VirtualFilesystem().list_stations())
