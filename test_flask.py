import flask
print("Flask version:", flask.__version__)
print("Flask location:", flask.__file__)
print("Has before_first_request?:", hasattr(flask.Flask, "before_first_request"))
print("dir(Flask):", dir(flask.Flask))