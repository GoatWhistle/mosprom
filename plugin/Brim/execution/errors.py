from ..protocol import constants


class OperationError(Exception):
    def __init__(self, code, message, details=None):
        Exception.__init__(self, message)
        self.code = code
        self.message = message
        self.details = details or {}


class OutcomeUnknown(OperationError):
    def __init__(self, message, details=None):
        OperationError.__init__(self, constants.ERR_OUTCOME_UNKNOWN, message, details)
