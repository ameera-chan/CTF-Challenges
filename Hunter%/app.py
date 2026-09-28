import os
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

from flask import Flask, Response, jsonify, make_response, request, send_from_directory
from graphql import graphql_sync

from field_guide import PUBLIC_BOARS, build_schema


BASE_DIR = Path(__file__).resolve().parent
SCHEMA = build_schema()
DEBUG_TOKEN = os.getenv("DEBUG_TOKEN", "caput-apri-defero")
MAX_PREVIEW_BYTES = 500
PUBLIC_FIELDS = ("Name", "Weight", "TuskScore", "Method", "Location", "Date")

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024


def _json_response(payload, status=200):
    response = make_response(jsonify(payload), status)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _build_document(boars, fields):
    selection = " ".join(fields)
    aliases = [
        f'_{index}: boar(name:"{name}") {{ {selection} }}'
        for index, name in enumerate(boars, start=1)
    ]
    return "{ " + " ".join(aliases) + " }"


def _is_full_introspection_dump(document):
    lowered = document.lower()
    return "__schema" in lowered and "types" in lowered and "fields" in lowered


def _is_local_request():
    return request.remote_addr in {"127.0.0.1", "::1"}


def _valid_preview_url(url):
    if not isinstance(url, str):
        return False
    lowered = url.lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        return False
    return "localhost" not in lowered and "127.0.0.1" not in lowered


def _numeric_host_to_ipv4(hostname):
    if not hostname:
        return None
    base = 10
    numeric = hostname
    if hostname.lower().startswith("0x"):
        base = 16
        numeric = hostname[2:]
    elif not hostname.isdigit():
        return None
    if not numeric:
        return None
    try:
        value = int(numeric, base)
    except ValueError:
        return None
    if value < 0 or value > 0xFFFFFFFF:
        return None
    return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/boars")
@app.get("/boars.html")
def boars_page():
    return send_from_directory(BASE_DIR, "boars.html")


@app.get("/sighting")
@app.get("/submit")
@app.get("/sighting.html")
def sighting_page():
    return send_from_directory(BASE_DIR, "sighting.html")


@app.get("/api/trophies")
def trophies():
    return _json_response([{key: boar[key] for key in PUBLIC_FIELDS} for boar in PUBLIC_BOARS])


@app.get("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(BASE_DIR / "assets", filename)


@app.get("/internal/debug-token")
def debug_token():
    if not _is_local_request() or request.headers.get("X-Hunter-Internal") != "preview":
        return _json_response({"error": "Not found"}, 404)
    return Response(DEBUG_TOKEN, mimetype="text/plain")


@app.post("/preview")
def preview():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_response({"error": "Invalid request body."}, 400)

    image_url = payload.get("imageUrl")
    if not _valid_preview_url(image_url):
        return _json_response({"error": "Invalid image URL."}, 400)

    parsed = urlparse(image_url)
    if not parsed.netloc:
        return _json_response({"error": "Invalid image URL."}, 400)

    fetch_url = image_url
    host_override = _numeric_host_to_ipv4(parsed.hostname)
    if host_override is not None:
        netloc = host_override
        if parsed.port is not None:
            netloc = f"{netloc}:{parsed.port}"
        fetch_url = urlunparse(parsed._replace(netloc=netloc))

    req = Request(
        fetch_url,
        headers={"User-Agent": "HunterPreview/1.0", "X-Hunter-Internal": "preview"},
    )
    try:
        with urlopen(req, timeout=4) as response:
            preview_text = response.read(MAX_PREVIEW_BYTES).decode("utf-8", errors="replace")
    except (URLError, TimeoutError):
        return _json_response({"error": "Failed to fetch the provided URL."}, 502)
    return _json_response({"preview": preview_text})


@app.post("/console")
def query_console():
    provided_token = request.headers.get("X-Debug-Token")
    if provided_token is None:
        return _json_response({"error": "Missing X-Debug-Token header"}, 403)
    if provided_token != DEBUG_TOKEN:
        return _json_response({"error": "Invalid X-Debug-Token header"}, 403)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json_response({"errors": [{"message": "Invalid request body."}]}, 400)

    boars = payload.get("boars")
    fields = payload.get("fields")
    if not isinstance(boars, list) or not isinstance(fields, list):
        return _json_response(
            {
                "errors": [
                    {
                        "message": (
                            "Invalid catalog request. Expected JSON object with "
                            "'boars' and 'fields' keys."
                        )
                    }
                ]
            },
            400,
        )
    if not boars or not fields or len(boars) > 20 or len(fields) > 16:
        return _json_response({"errors": [{"message": "Catalog request is out of range."}]}, 400)
    if not all(isinstance(value, str) and len(value) <= 4096 for value in boars):
        return _json_response({"errors": [{"message": "Invalid specimen selector."}]}, 400)
    if not all(isinstance(value, str) and len(value) <= 256 for value in fields):
        return _json_response({"errors": [{"message": "Invalid field selector."}]}, 400)

    document = _build_document(boars, fields)
    if _is_full_introspection_dump(document):
        return _json_response(
            {"errors": [{"message": "Full schema introspection exceeded runtime capacity."}]},
            500,
        )

    result = graphql_sync(SCHEMA, document)
    response = {}
    if result.data is not None:
        response["data"] = result.data
    if result.errors:
        response["errors"] = [{"message": error.message} for error in result.errors]
    return _json_response(response)


@app.errorhandler(413)
def request_too_large(_error):
    return _json_response({"errors": [{"message": "Request body is too large."}]}, 413)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
