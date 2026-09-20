"""Executed inside Embedded Python; fails the build if imports fail."""
import iris
import flask
from argus.app import app
assert app is not None
print('ARGUS_EMBEDDED_PYTHON_OK')
