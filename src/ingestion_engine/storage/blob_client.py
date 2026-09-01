from pathlib import Path

from azure.storage.blob import BlobServiceClient


class BlobClient:

    """
    A client for interacting with Azure Blob Storage.
    
    """

    def __init__(self, connection_string: str, container_name: str):

        self._service_client = BlobServiceClient.from_connection_string(connection_string)
        self._container_client = self._service_client.get_container_client(container_name)

    def upload_file(self, local_path: str | Path, blob_path: str, overwrite: bool = True) -> None:

        """
        Uploads a file to Azure Blob Storage.
        
        Args:
            local_path (str | Path): The local path of the file to upload.
            blob_path (str): The path of the blob in Azure Blob Storage.
            overwrite (bool, optional): Whether to overwrite the blob if it exists. Defaults to True.
        """

        local_path = Path(local_path)

        blob_client = self._container_client.get_blob_client(blob_path)

        with local_path.open("rb") as file:
            blob_client.upload_blob(file, overwrite=overwrite)

    def upload_text(self, content: str, blob_path: str, overwrite: bool = True) -> None:
        """
        Uploads text content to Azure Blob Storage.
        
        Args:
            content (str): The text content to upload.
            blob_path (str): The path of the blob in Azure Blob Storage.
            overwrite (bool, optional): Whether to overwrite the blob if it exists. Defaults to True.
        """
        
        blob_client = self._container_client.get_blob_client(blob_path)
        blob_client.upload_blob(content.encode("utf-8"), overwrite=overwrite)


    def delete_prefix(self, blob_prefix: str) -> None:

        """
        Deletes all blobs in the container that start with the specified prefix.

        Args:
            blob_prefix (str): The prefix of the blobs to delete.
        """
    
        prefix = blob_prefix.rstrip("/") + "/"

        blobs = self._container_client.list_blobs(name_starts_with=prefix)

        for blob in blobs:
            self._container_client.delete_blob(blob.name)

    def get_spark_path(self, blob_path: str) -> str:

        """
        Returns the Spark-compatible path for a blob in Azure Blob Storage.
        
        Args:
            blob_path (str): The path of the blob in Azure Blob Storage.
    
        Returns:
            str: The Spark-compatible path for the blob.
        """
        return (
            f"wasbs://{self._container_client.container_name}@"
            f"{self._service_client.account_name}.blob.core.windows.net/{blob_path}"
        )