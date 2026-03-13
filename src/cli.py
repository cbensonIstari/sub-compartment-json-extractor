"""Interactive CLI for extracting JSON elements from Istari files."""

import json
import sys

from .url_parser import parse_istari_url, validate_uuid
from .json_navigator import display_structure, resolve_path, preview_json, suggest_filename, describe_value
from .extractor import extract_element, write_temp_json, upload_to_istari, cleanup_temp_file
from .istari_client import create_client, fetch_file, read_file_json, get_latest_revision_id, get_file_display_info


def print_header():
    print()
    print("=" * 60)
    print("  Istari JSON Sub-Compartment Extractor")
    print("  Extract individual elements from JSON files in Istari")
    print("=" * 60)
    print()


def get_url_input() -> str:
    """Prompt for and validate an Istari file URL."""
    while True:
        url = input("Enter Istari file URL: ").strip()
        if not url:
            print("  URL cannot be empty. Try again.")
            continue

        try:
            parsed = parse_istari_url(url)
            if not validate_uuid(parsed["file_id"]):
                print(f"  Warning: '{parsed['file_id']}' doesn't look like a UUID, but proceeding anyway.")
            return url
        except ValueError as e:
            print(f"  Error: {e}")
            print("  Try again.\n")


def display_file_info(info: dict):
    """Display file metadata."""
    name = info.get("display_name") or info.get("name") or "Unknown"
    size = info.get("size")
    revisions = info.get("revision_count", 0)

    size_str = ""
    if size:
        if size > 1_000_000:
            size_str = f" ({size / 1_000_000:.1f} MB)"
        elif size > 1_000:
            size_str = f" ({size / 1_000:.1f} KB)"
        else:
            size_str = f" ({size} bytes)"

    print(f"\nFile: {name}{size_str}, {revisions} revision(s)")


def display_json_tree(data):
    """Show the JSON structure and return the top-level keys/indices for selection."""
    print("\nJSON Structure:")
    lines = display_structure(data, indent=0, max_depth=1)

    for display_line, _ in lines:
        print(f"  {display_line}")

    print()
    return lines


def get_element_selection(data, top_level_lines) -> str:
    """Prompt user to select an element to extract."""
    print("Select an element to extract:")
    print("  - Enter a number (e.g., 0) to select by index above")
    print("  - Enter a key name (e.g., \"components\")")
    print("  - Enter a dot-path (e.g., \"metadata.version\")")
    print("  - Enter a JSONPath (e.g., \"$.components[0]\")")
    print()

    while True:
        selection = input("Element to extract: ").strip()
        if not selection:
            print("  Selection cannot be empty. Try again.")
            continue

        # If it's a plain integer, map to the key at that index
        try:
            idx = int(selection)
            if isinstance(data, dict):
                keys = list(data.keys())
                if 0 <= idx < len(keys):
                    return keys[idx]
                else:
                    print(f"  Index {idx} out of range (0-{len(keys) - 1}). Try again.")
                    continue
            elif isinstance(data, list):
                if 0 <= idx < len(data):
                    return f"[{idx}]"
                else:
                    print(f"  Index {idx} out of range (0-{len(data) - 1}). Try again.")
                    continue
        except ValueError:
            pass

        # Validate the path resolves
        try:
            resolve_path(data, selection)
            return selection
        except (KeyError, IndexError) as e:
            print(f"  Error: {e}")
            print("  Try again.\n")


def confirm_upload() -> bool:
    """Ask user to confirm the upload."""
    while True:
        answer = input("Confirm upload to Istari? [Y/n]: ").strip().lower()
        if answer in ("", "y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please enter Y or N.")


def main():
    print_header()

    # Step 1: Connect to Istari
    print("Connecting to Istari...")
    try:
        client = create_client()
        print("  Connected.\n")
    except EnvironmentError as e:
        print(f"\nSetup Error: {e}")
        print("\nTo get started:")
        print("  1. Copy .env.example to .env")
        print("  2. Set ISTARI_REGISTRY_URL to your Istari instance URL")
        print("  3. Set ISTARI_AUTH_TOKEN to your Personal Access Token")
        print("     (Generate one at: Settings > Developer Settings in Istari)")
        sys.exit(1)
    except Exception as e:
        print(f"\nConnection Error: {e}")
        sys.exit(1)

    # Step 2: Get the file URL
    url = get_url_input()
    parsed = parse_istari_url(url)
    file_id = parsed["file_id"]

    # Step 3: Fetch the file
    print(f"\nFetching file {file_id}...")
    try:
        file_obj = fetch_file(client, file_id)
    except Exception as e:
        print(f"\nError fetching file: {e}")
        sys.exit(1)

    info = get_file_display_info(file_obj)
    display_file_info(info)

    # Step 4: Read and display JSON
    print("\nReading JSON content...")
    try:
        data = read_file_json(file_obj)
    except json.JSONDecodeError as e:
        print(f"\nError: File is not valid JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError reading file content: {e}")
        sys.exit(1)

    top_level_lines = display_json_tree(data)

    # Step 5: Select element
    path = get_element_selection(data, top_level_lines)

    # Step 6: Extract and preview
    element, leaf_key = extract_element(data, path)
    print(f'\nExtracted "{path}" ({describe_value(element)})')
    print(f"\nPreview:")
    print(preview_json(element))
    print()

    # Step 7: Confirm and upload
    if not confirm_upload():
        print("Upload cancelled.")
        sys.exit(0)

    # Step 8: Write temp file and upload
    original_name = info.get("name") or "file"
    filename = suggest_filename(original_name, leaf_key)
    description = f"Extracted '{path}' from {original_name}"

    print(f"\nUploading {filename}...")
    temp_path = write_temp_json(element, filename)

    try:
        revision_id = get_latest_revision_id(file_obj)
        new_file = upload_to_istari(
            client,
            file_path=temp_path,
            source_revision_id=revision_id,
            description=description,
            display_name=filename,
        )
        print(f"\nNew file created successfully!")
        print(f"  File ID: {new_file.id}")
        print(f"  Name:    {filename}")
        print(f"  Source traceability linked to revision: {revision_id}")

        # Construct the URL
        host = parsed["host"]
        workspace_id = parsed["workspace_id"]
        print(f"  URL:     https://{host}/files/{workspace_id}/{new_file.id}")
    except Exception as e:
        print(f"\nError uploading file: {e}")
        sys.exit(1)
    finally:
        cleanup_temp_file(temp_path)

    print("\nDone.")


if __name__ == "__main__":
    main()
