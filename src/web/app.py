import json
from flask import Flask, render_template, request, jsonify

from ..url_parser import parse_istari_url, validate_uuid
from ..json_navigator import resolve_path, preview_json, describe_value, suggest_filename
from ..extractor import extract_element, write_temp_json, upload_to_istari, cleanup_temp_file
from ..istari_client import create_client, fetch_file, read_file_json, get_latest_revision_id, get_file_display_info

app = Flask(__name__,
            template_folder="templates",
            static_folder="static")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/fetch-file", methods=["POST"])
def api_fetch_file():
    """Parse URL, fetch file metadata and JSON content from Istari."""
    try:
        url = request.json.get("url", "")
        parsed = parse_istari_url(url)
        file_id = parsed["file_id"]

        if not validate_uuid(file_id):
            return jsonify({"warning": f"'{file_id}' may not be a valid UUID"}), 200

        client = create_client()
        file_obj = fetch_file(client, file_id)
        info = get_file_display_info(file_obj)
        data = read_file_json(file_obj)
        revision_id = get_latest_revision_id(file_obj)

        return jsonify({
            "parsed": parsed,
            "file_info": info,
            "data": data,
            "revision_id": revision_id,
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/resolve-path", methods=["POST"])
def api_resolve_path():
    """Validate a path and return a preview of the selected element."""
    try:
        data = request.json["data"]
        path = request.json["path"]
        value = resolve_path(data, path)
        return jsonify({
            "value": value,
            "description": describe_value(value),
            "preview": preview_json(value, max_lines=40),
        })
    except (KeyError, IndexError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Re-fetch from Istari, extract element, upload as new file with traceability."""
    try:
        file_id = request.json["file_id"]
        path = request.json["path"]
        original_name = request.json["original_name"]
        host = request.json["host"]
        workspace_id = request.json["workspace_id"]

        client = create_client()
        file_obj = fetch_file(client, file_id)
        data = read_file_json(file_obj)
        revision_id = get_latest_revision_id(file_obj)

        element, leaf_key = extract_element(data, path)
        filename = suggest_filename(original_name, leaf_key)
        description = f"Extracted '{path}' from {original_name}"

        temp_path = write_temp_json(element, filename)
        try:
            new_file = upload_to_istari(
                client,
                file_path=temp_path,
                source_revision_id=revision_id,
                description=description,
                display_name=filename,
            )
            return jsonify({
                "success": True,
                "new_file_id": new_file.id,
                "url": f"https://{host}/files/{workspace_id}/{new_file.id}",
                "filename": filename,
                "revision_id": revision_id,
            })
        finally:
            cleanup_temp_file(temp_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
