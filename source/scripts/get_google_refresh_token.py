import os
import sys
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    print("==================================================")
    print("OAUTH 2.0 REFRESH TOKEN GENERATOR FOR GOOGLE DRIVE")
    print("==================================================")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.dirname(script_dir)
    default_secret = os.path.join(source_dir, "backend", "core", "client_secret.json")
    
    if os.path.exists(default_secret):
        client_secret_path = default_secret
    else:
        client_secret_path = "client_secret.json"
        
    if not os.path.exists(client_secret_path):
        print(f"Error: File '{client_secret_path}' not found!")
        return

    print(f"Using OAuth secrets: {client_secret_path}")
    print("Opening browser for Google Account authentication...")
    
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    creds = flow.run_local_server(port=0)
    
    print("\nSUCCESS! Your OAuth 2.0 Credentials:")
    print("--------------------------------------------------")
    print(f"CLIENT_ID     : {creds.client_id}")
    print(f"CLIENT_SECRET : {creds.client_secret}")
    print(f"REFRESH_TOKEN : {creds.refresh_token}")
    print("--------------------------------------------------")
    
    token_info = {
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri
    }
    
    out_path = os.path.join(source_dir, "backend", "core", "gdrive_oauth_token.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(token_info, f, indent=2)
    print(f"Saved token to '{out_path}'!")

if __name__ == "__main__":
    main()
