from pyspark.sql import DataFrame

from ingestion_engine.storage.blob_client import BlobClient


def write_df_to_geoparquet(df, blob_client, blob_path):
    # Sanitize the path for Azure compatibility
    blob_path_safe = blob_path.replace('+', 'Z').replace(':', '')
    
    spark_path = f"wasbs://{blob_client.container_name}@{blob_client.account_name}.blob.core.windows.net/{blob_path_safe}"
    
    df.write \
        .format("geoparquet") \
        .mode("overwrite") \
        .save(spark_path)