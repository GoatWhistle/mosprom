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


class LlmNotConfigured(DomainError):
    code = "llm_not_configured"
    message = "LLM connection is not configured for this instance"


class Unauthorized(DomainError):
    code = "unauthorized"
    message = "Instance token is missing or invalid"


class NotFound(DomainError):
    code = "not_found"
    message = "Resource not found"


class InstanceExists(DomainError):
    code = "instance_exists"
    message = "Instance is already registered"


class ContractMismatch(DomainError):
    code = "contract_mismatch"
    message = "Unsupported contract version"


class InvalidTransition(DomainError):
    code = "invalid_state_transition"
    message = "The requested transition is unavailable"


class RunActive(DomainError):
    code = "run_active"
    message = "Another run is active for this instance"


class RunNotWaiting(DomainError):
    code = "run_not_waiting"
    message = "Run is not waiting for this input"


class RunFinished(DomainError):
    code = "run_finished"
    message = "Run is already finished"


class NoPendingBatch(DomainError):
    code = "no_pending_batch"
    message = "There is no change batch waiting for confirmation"


class InvalidArtifact(DomainError):
    code = "invalid_artifact"
    message = "Artifact upload is invalid"


class ChecksumMismatch(InvalidArtifact):
    code = "checksum_mismatch"
    message = "Artifact checksum does not match"


class PayloadTooLarge(DomainError):
    code = "payload_too_large"
    message = "Payload exceeds the configured limit"


class InvalidRequest(DomainError):
    code = "invalid_request"
    message = "Request is invalid"
