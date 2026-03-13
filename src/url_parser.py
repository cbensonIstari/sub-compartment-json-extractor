from urllib.parse import urlparse
import re


def parse_istari_url(url: str) -> dict:
    """Parse an Istari file URL into its components.

    Accepts URLs like:
        https://demo.istari.app/files/{workspace_id}/{file_id}

    Returns dict with workspace_id, file_id, and host.
    """
    parsed = urlparse(url)

    if not parsed.scheme:
        parsed = urlparse("https://" + url)

    path_parts = [p for p in parsed.path.strip("/").split("/") if p]

    if len(path_parts) < 3 or path_parts[0] != "files":
        raise ValueError(
            f"Invalid Istari URL format. Expected: https://{{host}}/files/{{workspace_id}}/{{file_id}}\n"
            f"Got: {url}"
        )

    return {
        "host": parsed.netloc,
        "workspace_id": path_parts[1],
        "file_id": path_parts[2],
    }


def validate_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    return bool(pattern.match(value))
