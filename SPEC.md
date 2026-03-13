# JSON Sub-Compartment Extraction Tool — Product Spec

## Problem Statement

Istari users store large composite JSON files (e.g., system models, BOM manifests, configuration packages) as files in the platform. Today, there is no way to extract an individual element from a JSON file and promote it to its own standalone file in Istari — with full traceability back to the source.

This forces users to manually download, edit, and re-upload data, losing provenance and creating version-control gaps.

## User Story

> As an Istari user, I want to select a JSON file by its Istari URL, pick a specific element (by JSONPath or key), and create a new standalone file in Istari containing just that element — linked back to the original file as its source.

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. User provides an Istari file URL                            │
│     e.g. https://demo.istari.app/files/{workspace}/{file_id}    │
│                                                                 │
│  2. Tool parses the file_id from the URL                        │
│                                                                 │
│  3. Tool fetches the JSON content via Istari SDK                │
│     client.get_file(file_id) → file.read_json()                 │
│                                                                 │
│  4. User browses the JSON structure and selects an element      │
│     - Top-level keys shown as a navigable tree                  │
│     - User picks a key / JSONPath                               │
│                                                                 │
│  5. Tool extracts the selected element                          │
│                                                                 │
│  6. Tool writes the element to a temp file and uploads          │
│     via client.add_file(path, sources=[...], ...)               │
│     with a NewSource linking back to the original revision      │
│                                                                 │
│  7. User receives the new file's Istari URL                     │
└─────────────────────────────────────────────────────────────────┘
```

## Core Capabilities

### 1. URL Parsing
- Accept URLs in the format: `https://{host}/files/{workspace_id}/{file_id}`
- Extract the `file_id` (the SDK only needs this; workspace_id is routing-only)

### 2. JSON Fetch & Display
- Use `client.get_file(file_id)` then `file.read_json()` to load content
- Display the JSON structure to the user as a navigable tree
- Show top-level keys with type annotations (object, array, string, number, etc.)

### 3. Element Selection
- Support selection by:
  - **Top-level key** (e.g., `"engines"`)
  - **Dot-notation path** (e.g., `"vehicle.propulsion.engines"`)
  - **JSONPath expression** (e.g., `$.vehicle.propulsion.engines`)
  - **Array index** (e.g., `"components[2]"`)

### 4. Extraction & Upload
- Extract the selected sub-tree from the JSON
- Serialize it as pretty-printed JSON
- Write to a temporary local file named `{original_stem}_{element_key}.json`
- Upload via `client.add_file()` with:
  - `sources=[NewSource(revision_id=original_revision_id)]` for traceability
  - `description` auto-generated: `"Extracted '{key}' from {original_name}"`
  - `display_name` set to `{element_key}.json`

### 5. Traceability
- The new file links back to the exact revision of the source file via `NewSource`
- This creates a visible provenance chain in the Istari UI

## Technical Design

### SDK Methods Used

| Operation | SDK Call |
|-----------|----------|
| Get file by ID | `client.get_file(file_id)` |
| Read JSON content | `file.read_json()` |
| Get source revision ID | `file.revisions[-1].id` |
| Upload new file | `client.add_file(path, sources, description, display_name)` |
| Link provenance | `NewSource(revision_id=rev_id, relationship_identifier="extracted_from")` |

### URL Parsing Logic

```python
from urllib.parse import urlparse

def parse_istari_url(url: str) -> str:
    """Extract file_id from an Istari file URL."""
    path = urlparse(url).path          # /files/{workspace_id}/{file_id}
    parts = path.strip("/").split("/") # ["files", workspace_id, file_id]
    return parts[2]                    # file_id
```

### JSON Navigation

```python
def resolve_path(data: dict, path: str):
    """Navigate into a JSON structure by dot-notation or bracket path."""
    # Supports: "key", "key.subkey", "key[0].subkey", "key[0]"
    ...
```

### Architecture

```
sub_compartment_JSON/
├── SPEC.md                  # This spec
├── requirements.txt         # Python dependencies
├── src/
│   ├── __init__.py
│   ├── cli.py               # CLI entry point (interactive terminal UI)
│   ├── url_parser.py         # Istari URL → file_id extraction
│   ├── json_navigator.py     # JSON tree display + path resolution
│   ├── extractor.py          # Core extraction + upload logic
│   └── istari_client.py      # SDK client wrapper
├── .env.example             # Template for credentials
└── tests/
    ├── test_url_parser.py
    ├── test_json_navigator.py
    └── test_extractor.py
```

## CLI Interface

```
$ python -m src.cli

Enter Istari file URL: https://demo.istari.app/files/f7c6d97d-.../5ea06ed9-...

Fetching file from Istari...
File: system_model.json (245 KB, 3 revisions)

JSON Structure:
  [0] "metadata"        (object, 5 keys)
  [1] "components"      (array, 12 items)
  [2] "connections"     (object, 8 keys)
  [3] "parameters"      (object, 23 keys)
  [4] "requirements"    (array, 7 items)

Enter element to extract (key, path, or number): 1

Extracting "components" (array, 12 items)...

Preview (first 10 lines):
  [
    {
      "id": "comp-001",
      "name": "Main Engine",
      "type": "propulsion",
      ...

Confirm upload to Istari? [Y/n]: y

Uploading system_model_components.json...
New file created: https://demo.istari.app/files/f7c6d97d-.../a1b2c3d4-...
Source traceability linked to revision: rev-5ea06ed9
Done.
```

## Out of Scope (v1)

- Batch extraction of multiple elements at once
- Merging extracted elements back into a parent JSON
- Schema validation of extracted elements
- Web UI (CLI-only for prototype)
- Editing the extracted element before upload

## Success Criteria

1. User can paste an Istari file URL and see the JSON structure
2. User can select any element by key, path, or index
3. The selected element is uploaded as a new file in Istari
4. The new file has `sources` linking it back to the original revision
5. The entire flow works in < 30 seconds for typical JSON files (< 10 MB)
