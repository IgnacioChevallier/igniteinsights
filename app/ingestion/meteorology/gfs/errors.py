class GFSError(Exception):
    pass


class GFSCycleResolutionError(GFSError):
    pass


class GFSDownloadError(GFSError):
    pass
