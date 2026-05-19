class WorldCoverError(Exception):
    pass


class WorldCoverTileNotFoundError(WorldCoverError):
    pass


class WorldCoverDownloadError(WorldCoverError):
    pass
