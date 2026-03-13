import os
from dotenv import load_dotenv


def create_client():
    """Create and return an authenticated Istari SDK client.

    Reads credentials from environment variables (or .env file).
    """
    load_dotenv()

    registry_url = os.getenv("ISTARI_REGISTRY_URL")
    auth_token = os.getenv("ISTARI_AUTH_TOKEN")

    if not registry_url:
        raise EnvironmentError(
            "ISTARI_REGISTRY_URL not set. Copy .env.example to .env and fill in your credentials."
        )
    if not auth_token:
        raise EnvironmentError(
            "ISTARI_AUTH_TOKEN not set. Generate a Personal Access Token in Istari "
            "(Settings > Developer Settings) and add it to your .env file."
        )

    from istari_digital_client import Client, Configuration

    config = Configuration(
        registry_url=registry_url,
        registry_auth_token=auth_token,
    )

    return Client(config)


def fetch_file(client, file_id: str):
    """Fetch a file object from Istari by its ID."""
    return client.get_file(file_id=file_id)


def read_file_json(file_obj):
    """Read and parse the JSON content of an Istari file."""
    return file_obj.read_json()


def get_latest_revision_id(file_obj) -> str:
    """Get the revision ID of the latest revision of a file."""
    if not file_obj.revisions:
        raise ValueError("File has no revisions")
    return file_obj.revisions[-1].id


def get_file_display_info(file_obj) -> dict:
    """Extract display information from a file object."""
    return {
        "name": file_obj.name,
        "size": file_obj.size,
        "mime": getattr(file_obj, "mime_type", None),
        "revision_count": len(file_obj.revisions) if file_obj.revisions else 0,
        "display_name": getattr(file_obj, "display_name", None),
        "description": getattr(file_obj, "description", None),
    }
