import json
import re


def describe_value(value) -> str:
    """Return a human-readable type description of a JSON value."""
    if isinstance(value, dict):
        return f"object, {len(value)} keys"
    elif isinstance(value, list):
        return f"array, {len(value)} items"
    elif isinstance(value, str):
        preview = value[:40] + "..." if len(value) > 40 else value
        return f'string: "{preview}"'
    elif isinstance(value, bool):
        return f"boolean: {str(value).lower()}"
    elif isinstance(value, (int, float)):
        return f"number: {value}"
    elif value is None:
        return "null"
    return type(value).__name__


def display_structure(data, indent=0, max_depth=2) -> list[str]:
    """Build a list of display lines showing the JSON structure.

    Returns a list of (display_line, path_key) tuples for interactive selection.
    """
    lines = []

    if isinstance(data, dict):
        for i, (key, value) in enumerate(data.items()):
            prefix = "  " * indent
            desc = describe_value(value)
            lines.append((f"{prefix}[{i}] \"{key}\"  ({desc})", key))

            if indent < max_depth - 1 and isinstance(value, (dict, list)):
                sub = display_structure(value, indent + 1, max_depth)
                lines.extend(sub)

    elif isinstance(data, list):
        for i, item in enumerate(data):
            prefix = "  " * indent
            desc = describe_value(item)
            lines.append((f"{prefix}[{i}]  ({desc})", str(i)))

            if indent < max_depth - 1 and isinstance(item, (dict, list)):
                sub = display_structure(item, indent + 1, max_depth)
                lines.extend(sub)

    return lines


def resolve_path(data, path: str):
    """Navigate into a JSON structure using a dot/bracket path.

    Supports:
        "key"                  -> data["key"]
        "key.subkey"           -> data["key"]["subkey"]
        "key[0]"               -> data["key"][0]
        "key[0].subkey"        -> data["key"][0]["subkey"]
        "[0]"                  -> data[0]
        "$.key.subkey"         -> data["key"]["subkey"]  (JSONPath-style root)
    """
    path = path.strip()

    # Strip optional JSONPath root marker
    if path.startswith("$."):
        path = path[2:]
    elif path == "$":
        return data

    # Tokenize: split on dots, but keep bracket indices attached
    tokens = _tokenize_path(path)

    current = data
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(current, list):
                raise KeyError(f"Cannot index into {type(current).__name__} with [{token}]")
            if token < 0 or token >= len(current):
                raise IndexError(f"Index [{token}] out of range (length {len(current)})")
            current = current[token]
        else:
            if isinstance(current, dict):
                if token not in current:
                    raise KeyError(f"Key '{token}' not found. Available keys: {list(current.keys())}")
                current = current[token]
            elif isinstance(current, list):
                # Try interpreting as integer index
                try:
                    idx = int(token)
                    current = current[idx]
                except (ValueError, IndexError):
                    raise KeyError(f"Cannot access '{token}' on a list. Use an integer index.")
            else:
                raise KeyError(f"Cannot navigate into {type(current).__name__} with '{token}'")

    return current


def _tokenize_path(path: str) -> list:
    """Split a path string into a list of string keys and integer indices."""
    tokens = []
    # Match: word chars (key), or [digits] (index)
    pattern = re.compile(r'([^.\[\]]+)|\[(\d+)\]')

    for match in pattern.finditer(path):
        key, index = match.groups()
        if index is not None:
            tokens.append(int(index))
        elif key is not None:
            tokens.append(key)

    return tokens


def preview_json(value, max_lines: int = 15) -> str:
    """Pretty-print a JSON value, truncated to max_lines."""
    formatted = json.dumps(value, indent=2)
    lines = formatted.split("\n")
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + f"\n  ... ({len(lines) - max_lines} more lines)"
    return formatted


def suggest_filename(original_name: str, element_key: str) -> str:
    """Generate a filename for the extracted element."""
    # Strip extension from original
    stem = original_name
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]

    # Clean the element key for use in filenames
    safe_key = re.sub(r'[^\w\-.]', '_', str(element_key))
    return f"{stem}_{safe_key}.json"
