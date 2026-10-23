from enum import StrEnum


class Flow(StrEnum):
    CONTINUE = "continue"
    WAIT = "wait"
    SUSPEND = "suspend"
    HELP = "help"
