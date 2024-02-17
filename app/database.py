# database.py

import os
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# Decoding the base64 environment variable to get the credentials
encoded_credentials = os.getenv('FIREBASE_CREDENTIALS_BASE64')
decoded_credentials = base64.b64decode(encoded_credentials)
cred_dict = json.loads(decoded_credentials.decode('utf-8'))

# Initializing Firebase admin with the decoded credentials
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

db = firestore.client()  # Now you can use this `db` object to interact with Firestore
