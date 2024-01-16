# database.py

import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env file

cred_path = os.getenv('FIREBASE_CREDENTIALS')  # get the path from the environment variable
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

db = firestore.client()  # Now you can use this `db` object to interact with Firestore