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
    """Parse URL, fetch file metadata and JSON content from Istari.

    Handles two Istari URL formats:
      - /files/{workspace_id}/{file_id}  (direct file ID)
      - /files/{model_id}/{revision_id}  (Istari web app format)
    """
    try:
        url = request.json.get("url", "")
        parsed = parse_istari_url(url)
        second_id = parsed["file_id"]  # Could be file_id or revision_id

        if not validate_uuid(second_id):
            return jsonify({"warning": f"'{second_id}' may not be a valid UUID"}), 200

        client = create_client()

        # Try as a direct file ID first
        file_obj = None
        try:
            file_obj = fetch_file(client, second_id)
        except Exception:
            pass

        # If that failed, the URL is likely {model_id}/{revision_id}
        # (Istari web app uses this format)
        if file_obj is None:
            model_id = parsed["workspace_id"]
            revision_id_from_url = second_id
            try:
                # First check the model's own file
                model = client.get_model(model_id=model_id)
                for rev in model.file.revisions:
                    if rev.id == revision_id_from_url:
                        file_obj = model.file
                        break

                # If not found, check model artifacts
                if file_obj is None:
                    artifacts = client.list_model_artifacts(model_id=model_id, page=1, size=100)
                    for artifact in artifacts.items:
                        for rev in artifact.file.revisions:
                            if rev.id == revision_id_from_url:
                                file_obj = artifact.file
                                break
                        if file_obj is not None:
                            break
            except Exception:
                pass

            if file_obj is None:
                return jsonify({
                    "error": f"Could not find file. Tried as file ID and as revision ID under model {model_id}."
                }), 404

            # Update parsed to use the actual file_id
            parsed["file_id"] = file_obj.id

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
        model_id = request.json.get("model_id")

        client = create_client()
        file_obj = fetch_file(client, file_id)
        data = read_file_json(file_obj)
        revision_id = get_latest_revision_id(file_obj)

        # If we didn't get model_id from client, try to get it from the file
        if not model_id and getattr(file_obj, "resource_type", None) == "Model":
            model_id = file_obj.resource_id

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
                model_id=model_id,
            )
            # Istari web URL format: /files/{model_id}/{revision_id}
            new_rev_id = new_file.revisions[-1].id if new_file.revisions else new_file.id
            if model_id:
                new_url = f"https://{host}/files/{model_id}/{new_rev_id}"
            else:
                new_url = f"https://{host}/files/workspace/{new_file.id}"
            return jsonify({
                "success": True,
                "new_file_id": new_file.id,
                "url": new_url,
                "filename": filename,
                "revision_id": revision_id,
            })
        finally:
            cleanup_temp_file(temp_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
