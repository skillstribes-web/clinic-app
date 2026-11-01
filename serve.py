import os

from waitress import serve

from web import web

host = os.environ.get("CLINIC_HOST", "127.0.0.1")
port = int(os.environ.get("PORT", "8000"))

print("Clinic app running on http://" + host + ":" + str(port))
serve(web, host=host, port=port, threads=4)