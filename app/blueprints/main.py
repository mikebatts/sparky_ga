# main.py

from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request, current_app
from werkzeug.utils import secure_filename
from google.oauth2 import credentials as google_credentials
from app.utils import is_credentials_valid
from app.database import db  # Make sure this is correctly imported
from firebase_admin import storage  # Import Firebase storage
from google.analytics.admin import AnalyticsAdminServiceClient
from google.analytics.admin_v1alpha.types import ListAccountSummariesRequest

import logging


logging.basicConfig(level=logging.INFO)


main = Blueprint('main', __name__, url_prefix='/')



@main.route('/')
def index():
    credentials_valid = False

    if 'credentials' in session:
        credentials = google_credentials.Credentials(**session['credentials'])
        credentials_valid = is_credentials_valid(credentials)

    if not credentials_valid:
        return render_template('login.html')
    elif 'properties' not in session or 'selected_property' not in session:
        return render_template('select_property.html', credentials_valid=credentials_valid)
    else:
        return render_template('report.html', credentials_valid=credentials_valid)


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


@main.route('/onboarding')
def onboarding():
    return render_template('onboarding.html')


@main.route('/close_onboarding')
def close_onboarding():
    user_email = session.get('user_email')
    if user_email:
        # Logic to delete the user's document from Firebase
        users_ref = db.collection('users').document(user_email)
        users_ref.delete()

    # Clear session and redirect to login
    session.clear()
    return redirect(url_for('main.index'))


@main.route('/save_business_info', methods=['POST'])
def save_business_info():
    try:
        business_name = request.form.get('businessName')
        business_description = request.form.get('businessDescription')

        # Retrieve user's email from the session
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

        # Get a reference to the users collection in Firestore
        users_ref = db.collection('users')
        users_data = {
            'businessName': business_name,
            'businessDescription': business_description
        }

        # Handle the image upload
        if 'avatar' in request.files:
            image = request.files['avatar']
            if image.filename != '':
                filename = secure_filename(image.filename)
                bucket = storage.bucket('sparky-408720.appspot.com')  # Replace with your actual bucket name
                blob = bucket.blob(f"avatars/{filename}")

                logging.info(f"Uploading file to Firebase Storage: {filename}")
                blob.upload_from_file(image)
                image_url = blob.public_url

                blob.make_public()  # This line makes the file public
                logging.info(f"File made public: {blob.public_url}")

                users_data['avatar'] = image_url
            else:
                logging.warning("Avatar file name is empty.")

        users_ref.document(user_email).set(users_data, merge=True)
        logging.info(f"Business info updated for user: {user_email}")


        # Logging for debugging
        current_app.logger.info(f"Received business info for {user_email}: {users_data}")

        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"Error in save_business_info: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@main.route('/save_goals_preferences', methods=['POST'])
def save_goals_preferences():
    data = request.get_json()
    goals = data.get('goals')
    preferences = data.get('preferences')

    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

    users_ref = db.collection('users')
    users_ref.document(user_email).set({
        'goals': goals,
        'preferences': preferences
    }, merge=True)

    current_app.logger.info(f"Saved goals and preferences for {user_email}")

    return jsonify({'status': 'success'})



@main.route('/get_properties')
def get_properties():
    return jsonify({'properties': session.get('properties', [])})



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