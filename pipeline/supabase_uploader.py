"""
Step 4 — Supabase Storage Upload
Uploads the locally-saved slide PNGs to a public Supabase Storage bucket
and returns their public URLs so Instagram can fetch them.

Setup:
  1. Create a Storage bucket in your Supabase project.
  2. Set the bucket to "Public" so Instagram can access the URLs.
  3. Add SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and SUPABASE_STORAGE_BUCKET
     as GitHub Secrets.
"""
import logging
import os
from datetime import datetime
from pathlib import Path

from supabase import create_client

logger = logging.getLogger(__name__)


def upload_slides(local_paths: list[str]) -> list[str]:
    """
    Uploads each PNG in local_paths to Supabase Storage.
    Returns a list of public URLs in the same order.
    """
    supabase_url = os.environ["SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "carousel-images")

    client = create_client(supabase_url, service_key)

    # Use a timestamped folder so each run is isolated
    folder = datetime.utcnow().strftime("%Y/%m/%d/%H%M%S")
    public_urls: list[str] = []

    for path_str in local_paths:
        path = Path(path_str)
        storage_path = f"{folder}/{path.name}"

        logger.info(f"  Uploading {path.name} → {bucket}/{storage_path}")
        client.storage.from_(bucket).upload(
            path=storage_path,
            file=path.read_bytes(),
            file_options={"content-type": "image/png"},
        )

        public_url = client.storage.from_(bucket).get_public_url(storage_path)
        public_urls.append(public_url)
        logger.info(f"    Public URL: {public_url}")

    logger.info(f"Uploaded {len(public_urls)} slides to Supabase")
    return public_urls
