# __init__.py in the 'app' directory

# from flask import Flask
# from .blueprints.auth import auth
# from .blueprints.analytics import analytics
# from .blueprints.reports import reports
# from .blueprints.main import main
# from .config import FLASK_APP_SECRET_KEY
# from .database import db  # Import the Firestore client
# import os
# import firebase_admin
# from firebase_admin import credentials, initialize_app




# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# app = Flask(__name__, static_folder='../static')
# app.secret_key = FLASK_APP_SECRET_KEY

# app.register_blueprint(auth)
# app.register_blueprint(analytics)
# app.register_blueprint(reports)
# app.register_blueprint(main)

# if __name__ == '__main__':
#     app.run('localhost', 8080, debug=True)

from flask import Flask
from app.blueprints.auth import auth
from app.blueprints.analytics import analytics
from app.blueprints.reports import reports
from app.blueprints.main import main
import firebase_admin
from firebase_admin import credentials, storage, firestore
from app.config import FLASK_APP_SECRET_KEY
import os
import json
import base64

# Decode Firebase credentials from the base64 environment variable
encoded_credentials = os.getenv('FIREBASE_CREDENTIALS_BASE64')
if encoded_credentials:
    cred_json = json.loads(base64.b64decode(encoded_credentials).decode('utf-8'))
    cred = credentials.Certificate(cred_json)
    firebase_admin.initialize_app(cred, {
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET').replace('gs://', '')
    })
else:
    raise ValueError("The FIREBASE_CREDENTIALS_BASE64 environment variable is not set.")

# Ensure the OAUTHLIB_INSECURE_TRANSPORT environment variable is set to '1'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Initialize the Flask application
app = Flask(__name__, static_folder='../static')
app.secret_key = FLASK_APP_SECRET_KEY

# Register the blueprints
app.register_blueprint(auth)
app.register_blueprint(analytics)
app.register_blueprint(reports)
app.register_blueprint(main)

# Run the app if this file is executed as the main program
if __name__ == '__main__':
    app.run('localhost', 8080, debug=True)
