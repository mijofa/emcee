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
data = {'ABC': ['ABC',
                'ABC HD',
                'ABC2  ABC4',
                'ABC3',
                'ABC News 24',
                'ABC Jazz',
                'Double J'],
        'Internal': ['PPC Local 1', 'PPC Local 2'],
        'Nine Network Australia': ['9HD',
                                   'Nine Melbourne',
                                   '9Life',
                                   'EXTRA',
                                   'GEM',
                                   'GO!',
                                   'WIN'],
        'SBS': ['SBS HD',
                'SBS ONE',
                'SBS TWO',
                'Food Network',
                'NITV',
                'SBS Radio 1',
                'SBS Radio 2',
                'SBS Radio 3'],
        'Seven Network': ['7 Digital', '7flix', '7mate', '7TWO', 'Racing'],
        'WIN Television': ['WIN Canberra',
                           'WIN Canberra HD',
                           'ELEVEN Canberra',
                           'ONE Canberra',
                           'TVSN',
                           'GOLD'],
        'Southern Cross': ['9Life',
                           'Nine Canberra',
                           'Aspire',
                           '9Go!',
                           '9HD Canberra',
                           'YESSHOP',
                           '9Gem'],
        }

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

            if os.path.isfile('{}/{}/folder.svg'.format(TVDIR, station_title)):
                icon_filename = '{}/{}/folder.svg'.format(TVDIR, station_title)
            elif os.path.isfile('{}/{}/folder.gif'.format(TVDIR, station_title)):
                icon_filename = '{}/{}/folder.gif'.format(TVDIR, station_title)
            else:
                icon_filename = None

            stations.append(Station(
                title=station_title,
                icon=icon_filename,  # FIXME: Make this use a file-object or similar
                channels=station_channels,
            ))

        return stations
