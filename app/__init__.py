# __init__.py in the 'app' directory

from flask import Flask
from .blueprints.auth import auth
from .blueprints.analytics import analytics
from .blueprints.reports import reports
from .blueprints.main import main
from .config import FLASK_APP_SECRET_KEY
import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env file

cred_path = os.getenv('FIREBASE_CREDENTIALS')  # get the path from the environment variable
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

db = firestore.client()  # Now you can use this `db` object to interact with Firestore

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__, static_folder='../static')
app.secret_key = FLASK_APP_SECRET_KEY

app.register_blueprint(auth)
app.register_blueprint(analytics)
app.register_blueprint(reports)
app.register_blueprint(main)

if __name__ == '__main__':
    app.run('localhost', 8080, debug=True)