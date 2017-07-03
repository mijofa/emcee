# This is intended as a wrapper between Emcee and whatever backing store is used behind it.
# For now however, it just returns the lists I want for testing, I'll implement the actual backing store later


class VirtualFilesystem():
    def list_stations(self):
        return ['ABC', 'Internal', 'Nine Network Australia', 'SBS', 'Seven Network']

    def list_channels(self, station):
        if station == "ABC":
            return ["ABC2  ABC4", "ABC3", "ABC HD", "ABC", "ABC Jazz", "ABC News 24", "Double J"]
        elif station == "Internal":
            return ["PPC Local 1", "PPC Local 2"]
        elif station == "Nine Network Australia":
            return ["9HD", "9Life", "EXTRA", "GEM", "GO!", "Nine Melbourne", "WIN"]
        elif station == "SBS":
            return ["Food Network", "NITV", "SBS HD", "SBS ONE", "SBS Radio 1", "SBS Radio 2", "SBS Radio 3", "SBS TWO"]
        elif station == "Seven Network":
            return ["7 Digital", "7flix", "7mate", "7TWO", "Racing"]

    def get_icon(self, channel, station):
        raise NotImplementedError()

    def get_info(self, channel, station):
        raise NotImplementedError()
