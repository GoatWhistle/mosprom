class DomainError(Exception):
    code = "domain_error"
    message = "Request failed"

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class ModelFailure(DomainError):
    code = "model_failure"
    message = "Language model failed"


class ModelTimeout(ModelFailure):
    code = "model_timeout"
    message = "Language model timed out"


class ModelMalformedResponse(ModelFailure):
    code = "model_malformed_response"
    message = "Language model returned an unusable response"


class Unauthorized(DomainError):
    code = "unauthorized"
    message = "Bearer token with a Claude OAuth token is required"


class InvalidRequest(DomainError):
    code = "invalid_request"
    message = "Request is invalid"
