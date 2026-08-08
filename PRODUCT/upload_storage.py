import os
from supabase import create_client, Client

SUPABASE_URL = "https://tlbdkjboznmtnazhjtxh.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRsYmRramJvem5tdG5hemhqdHhoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYxMzU2MjgsImV4cCI6MjEwMTcxMTYyOH0.z4PhM6P2odPnK6HJ10MMasDXpT0_jyqvZNXer9fa78U"
BUCKET_NAME = "pnx-userdata"

USER_DATA_DIR = r"D:\PNX App\QA Confirm Gate\PRODUCT\Local - Demo App\User Data"

def main():
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Try to get bucket, if error, it might not exist or we might not have permission
    try:
        bucket = supabase.storage.get_bucket(BUCKET_NAME)
        print(f"Bucket {BUCKET_NAME} found.")
    except Exception as e:
        print(f"Bucket {BUCKET_NAME} not found or error: {e}. Trying to create...")
        try:
            supabase.storage.create_bucket(BUCKET_NAME, options={"public": True})
            print(f"Bucket {BUCKET_NAME} created successfully.")
        except Exception as create_e:
            print(f"Could not create bucket: {create_e}")
            
    print("Uploading files...")
    count = 0
    for root, _, files in os.walk(USER_DATA_DIR):
        for file in files:
            if file == 'database.db':
                continue # Skip the stray db file in user data
                
            local_path = os.path.join(root, file)
            # Calculate relative path for Supabase
            rel_path = os.path.relpath(local_path, USER_DATA_DIR)
            supabase_path = rel_path.replace("\\", "/") # Convert Windows slashes to forward slashes
            
            with open(local_path, 'rb') as f:
                try:
                    # Upload or update file
                    supabase.storage.from_(BUCKET_NAME).upload(
                        path=supabase_path,
                        file=f,
                        file_options={"upsert": "true"}
                    )
                    print(f"Uploaded: {supabase_path}")
                    count += 1
                except Exception as e:
                    print(f"Failed to upload {supabase_path}: {e}")
                    
    print(f"Finished uploading {count} files.")

if __name__ == "__main__":
    main()
