class FIRMSClientError(Exception):
    pass


class FIRMSAuthError(FIRMSClientError):
    pass


class FIRMSEmptyResponseError(FIRMSClientError):
    pass
