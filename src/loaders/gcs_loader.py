import json
import logging

from google.cloud import storage

logger = logging.getLogger(__name__)


class GCSLoader:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

    def upload_raw_payload(
        self, destination_blob_name: str, payload_dict: dict
    ) -> bool:
        """Uploads a raw payload in JSON format to GCS."""
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_string(
                data=json.dumps(payload_dict, indent=2),
                content_type="application/json",
            )
            logger.info(
                f"Successfully uploaded to GCS: {destination_blob_name}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to upload to GCS {destination_blob_name}: {e}"
            )
            return False
