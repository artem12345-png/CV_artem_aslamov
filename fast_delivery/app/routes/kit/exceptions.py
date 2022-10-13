class KITError(Exception):
    pass


class KITApiError(KITError):
    pass


class KITFillerError(KITError):
    pass


class KITStatusException(KITError):
    pass

