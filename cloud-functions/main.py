import pandas as pd
import functions_framework
from google.cloud import bigquery, storage
import io
import logging

# Initialize clients
storage_client = storage.Client()
bigquery_client = bigquery.Client()

# Define BigQuery dataset & tables
BQ_DATASET = "bordereaux"
TABLES = {
    "policy": "stg_policy_bordereaux",
    "claim": "stg_claim_bordereaux",
    "payment": "stg_payment_bordereaux"
}

@functions_framework.cloud_event
def process_bordereaux(event):
    """Triggered when a new file is uploaded to GCS"""
    try:
        # Get file details
        bucket_name = event.data["bucket"]
        file_name = event.data["name"]
        
        # Determine the Bordereaux type
        if "policy" in file_name.lower():
            bordereaux_type = "policy"
        elif "claim" in file_name.lower():
            bordereaux_type = "claim"
        elif "payment" in file_name.lower():
            bordereaux_type = "payment"
        else:
            logging.warning(f"Unknown Bordereaux type for file: {file_name}")
            return

        table_name = TABLES[bordereaux_type]
        
        # Download file from GCS
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        data = blob.download_as_text()
        
        # Load into a Pandas DataFrame
        df = pd.read_csv(io.StringIO(data))
        
        # Upload to BigQuery (Auto-detect schema)
        job_config = bigquery.LoadJobConfig(
            autodetect=True,
            write_disposition="WRITE_APPEND"
        )
        job = bigquery_client.load_table_from_dataframe(df, f"{BQ_DATASET}.{table_name}", job_config=job_config)
        job.result()  # Wait for job to complete
        
        logging.info(f"✅ Successfully processed {file_name} into {table_name}")

    except Exception as e:
        logging.error(f"❌ Error processing file {file_name}: {str(e)}")
