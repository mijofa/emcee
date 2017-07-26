# This is intended as a wrapper between Emcee and whatever backing store is used behind it.
# For now however, it just returns the lists I want for testing, I'll implement the actual backing store later

import os
import sys
import collections
import random

TVDIR = '/home/mike/Videos/tv'

Station = collections.namedtuple('Station', 'title icon channels')
Channel = collections.namedtuple('Channel', 'title icon epg_brief uri')
EPG_brief = collections.namedtuple('EPG_brief', 'now next next_starttime')

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
    random.shuffle(epg_samples)


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
                    epg_brief=EPG_brief(
                        now=epg_samples[ind],
                        next=epg_samples[ind + 1],
                        next_starttime="23:59am",
                    ),
                    uri='{}'.format(sys.argv[1]),
                ))
                ind += 2

            stations.append(Station(
                title=station_title,
                icon=station_channels[0].icon,  # FIXME: Make this use a file-object or similar
                channels=station_channels,
            ))

        return stations
