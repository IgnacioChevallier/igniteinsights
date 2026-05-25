class CanopyError(Exception):
    pass


class CanopyDownloadError(CanopyError):
    pass


class CanopyTileNotFoundError(CanopyError):
    pass
