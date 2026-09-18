"""PythonAnywhere WSGI entry point.

On PythonAnywhere's Web tab, point the WSGI configuration file's content at
this module (or just add the two lines below into the file it gives you),
adjusting the path to wherever you cloned this repo.
"""
import sys

PROJECT_DIR = "/home/YOUR_USERNAME/wheel-of-fortune"
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import app as application  # noqa: E402
