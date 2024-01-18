# main.py

from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request, current_app
from werkzeug.utils import secure_filename
from google.oauth2 import credentials as google_credentials
from app.utils import is_credentials_valid
from app.database import db  # Make sure this is correctly imported
from firebase_admin import storage  # Import Firebase storage
from google.analytics.admin import AnalyticsAdminServiceClient
from google.analytics.admin_v1alpha.types import ListAccountSummariesRequest

import base64
import io
from PIL import Image

import logging


logging.basicConfig(level=logging.INFO)


# Utility function to convert credentials to a dictionary
def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}

main = Blueprint('main', __name__, url_prefix='/')



# @main.route('/')
# def index():
#     credentials_valid = False

#     if 'credentials' in session:
#         credentials = google_credentials.Credentials(**session['credentials'])
#         credentials_valid = is_credentials_valid(credentials)

#     if not credentials_valid:
#         return render_template('login.html')
#     elif 'properties' not in session or 'selected_property' not in session:
#         return render_template('select_property.html', credentials_valid=credentials_valid)
#     else:
#         return render_template('report.html', credentials_valid=credentials_valid)

@main.route('/')
def index():
    if 'logged_in' in session and session['logged_in']:
        if 'credentials' in session and is_credentials_valid(google_credentials.Credentials(**session['credentials'])):
            return redirect(url_for('main.select_property'))
        else:
            flash("Your session has expired. Please sign in again.", "error")
            return redirect(url_for('auth.authorize'))
    else:
        return render_template('login.html')  # Show login page if not logged in




@main.route('/select_property')
def select_property():
    if 'credentials' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('auth.authorize'))

    credentials = google_credentials.Credentials(**session['credentials'])
    admin_client = AnalyticsAdminServiceClient(credentials=credentials)

    properties_list = []
    try:
        account_summaries = admin_client.list_account_summaries(ListAccountSummariesRequest())
        for account in account_summaries.account_summaries:
            for property_summary in account.property_summaries:
                property_id = property_summary.property.split('/')[-1]
                formatted_name = f"{property_summary.display_name} - {property_summary.property_type} ({property_id})"
                properties_list.append({
                    'account_id': account.account,
                    'property_id': property_id,
                    'formatted_name': formatted_name,
                    'property_type': 'GA4'
                })
    except Exception as e:
        current_app.logger.error(f"Error fetching GA4 properties: {e}")
        flash('Error fetching properties.', 'error')

    return render_template('select_property.html', properties=properties_list)


@main.route('/edit_profile')
def edit_profile():
    # Ensure the user is logged in and fetch the necessary data
    return render_template('edit_profile.html')






@main.route('/onboarding')
def onboarding():
    is_new_user = True  # Or set this based on your application logic
    return render_template('onboarding.html', is_new_user=is_new_user)




@main.route('/close_onboarding')
def close_onboarding():
    # Clear session and redirect to login
    session.clear()
    return redirect(url_for('main.index'))



# @main.route('/save_business_info', methods=['POST'])
# def save_business_info():
#     try:
#         business_name = request.form.get('businessName')
#         business_description = request.form.get('businessDescription')

#         # Retrieve user's email from the session
#         user_email = session.get('user_email')
#         if not user_email:
#             return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

#         # Get a reference to the users collection in Firestore
#         users_ref = db.collection('users')
#         users_data = {
#             'businessName': business_name,
#             'businessDescription': business_description
#         }

#         # Handle the image upload
#         if 'avatar' in request.files:
#             image = request.files['avatar']
#             if image.filename != '':
#                 filename = secure_filename(image.filename)
#                 bucket = storage.bucket('sparky-408720.appspot.com')  # Replace with your actual bucket name
#                 blob = bucket.blob(f"avatars/{filename}")

#                 logging.info(f"Uploading file to Firebase Storage: {filename}")
#                 blob.upload_from_file(image)
#                 image_url = blob.public_url

#                 blob.make_public()  # This line makes the file public
#                 logging.info(f"File made public: {blob.public_url}")

#                 users_data['avatar'] = image_url
#             else:
#                 logging.warning("Avatar file name is empty.")

#         users_ref.document(user_email).set(users_data, merge=True)
#         logging.info(f"Business info updated for user: {user_email}")


#         # Logging for debugging
#         current_app.logger.info(f"Received business info for {user_email}: {users_data}")

#         return jsonify({'status': 'success'})
#     except Exception as e:
#         logging.error(f"Error in save_business_info: {e}")
#         return jsonify({'status': 'error', 'message': str(e)}), 500


# @main.route('/save_goals_preferences', methods=['POST'])
# def save_goals_preferences():
#     data = request.get_json()
#     goals = data.get('goals')
#     preferences = data.get('preferences')

#     user_email = session.get('user_email')
#     if not user_email:
#         return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

#     users_ref = db.collection('users')
#     users_ref.document(user_email).set({
#         'goals': goals,
#         'preferences': preferences
#     }, merge=True)

#     current_app.logger.info(f"Saved goals and preferences for {user_email}")

#     return jsonify({'status': 'success'})



@main.route('/complete_onboarding', methods=['POST'])
def complete_onboarding():
    try:
        data = request.get_json()
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

        users_ref = db.collection('users')

        # Process avatar if it exists in the data
        if 'avatarBase64' in data:
            avatar_data = data.pop('avatarBase64')
            avatar_image = base64.b64decode(avatar_data.split(',')[1])
            image = Image.open(io.BytesIO(avatar_image))
            filename = f"{user_email}_avatar.png"
            blob = storage.bucket('your-firebase-bucket').blob(f'avatars/{filename}')
            blob.upload_from_string(image.tobytes(), content_type='image/png')
            blob.make_public()
            data['avatarURL'] = blob.public_url  # Storing the URL of the uploaded image

        users_ref.document(user_email).set(data, merge=True)

        # Check if credentials are available in the session and convert them
        if 'credentials' in session and session['credentials']:
            session['logged_in'] = True
            session['credentials'] = credentials_to_dict(google_credentials.Credentials(**session['credentials']))
        else:
            return jsonify({'status': 'error', 'message': 'Credentials not found in session'}), 401

        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Error in complete_onboarding: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500







@main.route('/get_properties')
def get_properties():
    return jsonify({'properties': session.get('properties', [])})


@main.route('/account')
def account():
    # Your code to display the account page goes here
    return render_template('account.html')





@main.route('/reset_and_fetch')
def reset_and_fetch():
    # Reset the selected property in the session
    session.pop('selected_property', None)

    # Check if credentials are valid
    credentials_valid = False
    if 'credentials' in session:
        credentials = google_credentials.Credentials(**session['credentials'])
        credentials_valid = is_credentials_valid(credentials)

    if credentials_valid:
        # If credentials are valid, redirect to property selection
        return redirect(url_for('main.index'))
    else:
        # If credentials are not valid, redirect to login
        flash("Your session has expired. Please sign in with your Google account again.", "error")
        return redirect(url_for('auth.authorize'))