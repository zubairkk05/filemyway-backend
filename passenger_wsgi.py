"""cPanel / Phusion Passenger entry point.

cPanel runs Python apps through Phusion Passenger, which expects a WSGI
callable named ``application``. FastAPI is ASGI, so we wrap it with ``a2wsgi``.

In cPanel -> "Setup Python App" set:

    Application startup file:  passenger_wsgi.py
    Application Entry point:   application

Then install the requirements into the app's virtualenv and restart.
"""

import sys
from pathlib import Path

# Passenger may run with a different CWD; make the ``app`` package importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from a2wsgi import ASGIMiddleware  # noqa: E402
from app.main import app as asgi_app  # noqa: E402

# Passenger looks for this name.
application = ASGIMiddleware(asgi_app)
