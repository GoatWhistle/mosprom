def getMetaData():
    return {}


def register(app):
    from . import BrimExtension
    return {"extension": BrimExtension.BrimExtension(app)}
