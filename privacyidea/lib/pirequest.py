import flask


class PiRequestClass(flask.Request):
    all_data: dict
