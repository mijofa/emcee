# This is intended as a wrapper between Emcee and whatever backing store is used behind it.
# For now however, it just returns the lists I want for testing, I'll implement the actual backing store later

import os
import sys
import collections
import random
import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib

TVDIR = '/home/mike/Videos/tv'

# Test data.
data = {'ABC': ['ABC News 24',
                'ABC',
                'ABC2 KIDS',
                'ABC ME',
                'ABC HD',
                'Double J',
                'ABC Jazz'],
        'C31': ['C31'],
        'Nine Network Australia': ['Nine Melbourne',
                                   '9HD Melbourne',
                                   'GO!',
                                   '9Life',
                                   'Extra',
                                   'GEM'],
        'SBS': ['SBS ONE',
                'SBS TWO',
                'Food Network',
                'NITV',
                'SBS HD',
                'SBS Radio 1',
                'SBS Radio 2',
                'SBS Radio 3'],
        'Seven Network': ['7 Digital',
                          '7TWO',
                          '7mate',
                          '7flix Melbourne',
                          'TV4ME',
                          'RACING.COM'],
        'Ten Melbourne': ['TEN Digital', 'TVSN', 'ONE', 'ELEVEN', 'SpreeTV']}


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
        for station_title in sorted(data):

            station_channels = []
            for channel_title in data.get(station_title):
                if os.path.isfile('{}/{}/{}.svg'.format(TVDIR, station_title, channel_title)):
                    icon_filename = '{}/{}/{}.svg'.format(TVDIR, station_title, channel_title)
                elif os.path.isfile('{}/{}/{}.gif'.format(TVDIR, station_title, channel_title)):
                    icon_filename = '{}/{}/{}.gif'.format(TVDIR, station_title, channel_title)
                else:
                    icon_filename = None
                station_channels.append(Channel(
                    title=channel_title,
                    icon=icon_filename,  # FIXME: Make this use a file-object or similar
                    uri='{}'.format(sys.argv[-1]),
                ))
                ind += 2

            stations.append(Station(
                title=station_title,
                icon=station_channels[0].icon,  # FIXME: Make this use a file-object or similar
                channels=station_channels,
            ))

        return stations
