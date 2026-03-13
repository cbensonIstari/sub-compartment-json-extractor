import json
import tempfile
import os

from .json_navigator import resolve_path, suggest_filename


def extract_element(data, path: str) -> tuple:
    """Extract an element from a JSON structure by path.

    Returns (extracted_value, leaf_key) where leaf_key is the final
    key/index used in the path (for naming purposes).
    """
    element = resolve_path(data, path)

    # Determine the leaf key for naming
    leaf_key = path.split(".")[-1] if "." in path else path
    # Strip brackets if it's an index
    if leaf_key.startswith("[") and leaf_key.endswith("]"):
        leaf_key = leaf_key[1:-1]

    return element, leaf_key


def write_temp_json(data, filename: str) -> str:
    """Write JSON data to a temporary file. Returns the file path."""
    temp_dir = tempfile.mkdtemp(prefix="istari_extract_")
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return file_path


def upload_to_istari(client, file_path: str, source_revision_id: str,
                     description: str, display_name: str):
    """Upload the extracted JSON as a new file in Istari with source traceability."""
    from istari_digital_client import NewSource

    sources = [
        NewSource(
            revision_id=source_revision_id,
            relationship_identifier="extracted_from",
        )
    ]

    new_file = client.add_file(
        path=file_path,
        sources=sources,
        description=description,
        display_name=display_name,
    )

    return new_file


def cleanup_temp_file(file_path: str):
    """Remove a temporary file and its parent directory."""
    try:
        os.unlink(file_path)
        os.rmdir(os.path.dirname(file_path))
    except OSError:
        pass
