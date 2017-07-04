# This is intended as a wrapper between Emcee and whatever backing store is used behind it.
# For now however, it just returns the lists I want for testing, I'll implement the actual backing store later

import os
import collections

Station = collections.namedtuple('Station', 'title icon channels')
Channel = collections.namedtuple('Channel', 'title icon epg_brief uri')

# Test data.
data = {'ABC': ['ABC2  ABC4',
                'ABC3',
                'ABC HD',
                'ABC',
                'ABC Jazz',
                'ABC News 24',
                'Double J'],
        'Internal': ['PPC Local 1', 'PPC Local 2'],
        'Nine Network Australia': ['9HD',
                                   '9Life',
                                   'EXTRA',
                                   'GEM',
                                   'GO!',
                                   'Nine Melbourne',
                                   'WIN'],
        'SBS': ['Food Network',
                'NITV',
                'SBS HD',
                'SBS ONE',
                'SBS Radio 1',
                'SBS Radio 2',
                'SBS Radio 3',
                'SBS TWO'],
        'Seven Network': ['7 Digital', '7flix', '7mate', '7TWO', 'Racing']}


class VirtualFilesystem():
    def list_stations(self):
        stations = []
        for station_title in sorted(data):

            station_channels = []
            for channel_title in data.get(station_title):
                icon_filename = '/home/mike/Videos/tv/{}/{}.gif'.format(station_title, channel_title)
                station_channels.append(Channel(
                    title=channel_title,
                    icon=icon_filename if os.path.isfile(icon_filename) else None,  # FIXME: Make this use a file-object or similar
                    epg_brief=('now', 'next'),
                    uri='file:///dev/null',
                ))

            icon_filename = '/home/mike/Videos/tv/{}/folder.gif'.format(station_title)
            stations.append(Station(
                title=station_title,
                icon=icon_filename if os.path.isfile(icon_filename) else None,  # FIXME: Make this use a file-object or similar
                channels=station_channels,
            ))

        return stations
