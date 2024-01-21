# main.py

from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request, current_app
from werkzeug.utils import secure_filename
from google.oauth2 import credentials as google_credentials
from app.utils import is_credentials_valid
from app.database import db  # Make sure this is correctly imported
import firebase_admin
from firebase_admin import storage 
from google.analytics.admin import AnalyticsAdminServiceClient
from google.analytics.admin_v1alpha.types import ListAccountSummariesRequest
import os

import base64
import io
from PIL import Image

import logging


logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)


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
    user_email = session.get('user_email')
    if not user_email:
        return redirect(url_for('auth.login'))
    user_doc = db.collection('users').document(user_email).get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        # Make sure user_data contains 'avatar', 'businessName', 'businessDescription', 'goals', 'preferences'
        return render_template('edit_profile.html', user_data=user_data)
    else:
        flash("User data not found.", "error")
        return redirect(url_for('main.index'))



@main.route('/update_profile', methods=['POST'])
def update_profile():
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

    data = request.get_json()
    users_ref = db.collection('users')
    users_ref.document(user_email).update({
        'businessName': data['businessName'],
        'businessDescription': data['businessDescription'],
        'avatar': data['avatar']
    })

    return jsonify({'status': 'success'})

@main.route('/update_complete_profile', methods=['POST'])
def update_complete_profile():
    user_email = session.get('user_email')
    if not user_email:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

    data = request.get_json()
    users_ref = db.collection('users')
    users_ref.document(user_email).update({
        'businessName': data.get('businessName'),
        'businessDescription': data.get('businessDescription'),
        'avatar': data.get('avatar'),
        'goals': data.get('goals'),
        'preferences': data.get('preferences')
    })

    return jsonify({'status': 'success'})





@main.route('/onboarding')
def onboarding():
    is_new_user = True  # Or set this based on your application logic
    return render_template('onboarding.html', is_new_user=is_new_user)


@main.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    try:
        avatar_file = request.files['avatar']
        if avatar_file:
            filename = secure_filename(avatar_file.filename)
            print(f"Received file: {filename}")  # Debugging

            # Ensure bucket name is specified correctly
            bucket_name = os.getenv('FIREBASE_STORAGE_BUCKET').replace('gs://', '')
            print(f"Bucket name: {bucket_name}")  # Debugging

            bucket = storage.bucket(bucket_name, app=firebase_admin.get_app())
            blob = bucket.blob(f'avatars/{filename}')

            blob.upload_from_file(avatar_file.stream, content_type=avatar_file.content_type)
            blob.make_public()
            avatar_url = blob.public_url

            print(f"Avatar URL: {avatar_url}")  # Debugging

            # Update Firestore user document with the avatar URL
            user_email = session.get('user_email')
            if user_email:
                users_ref = db.collection('users')
                users_ref.document(user_email).update({'avatar': avatar_url})
                session['user_avatar'] = avatar_url

            return jsonify({'status': 'success', 'avatarURL': avatar_url})
        else:
            print("No avatar file provided")  # Debugging
            return jsonify({'status': 'error', 'message': 'No avatar file provided'}), 400
    except Exception as e:
        print(f"Error in upload_avatar: {e}")  # Debugging
        return jsonify({'status': 'error', 'message': str(e)}), 500


    

@main.route('/save_business_info', methods=['POST'])
def save_business_info():
    try:
        data = request.get_json()
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

        # Save business info to Firestore
        users_ref = db.collection('users')
        users_ref.document(user_email).update({
            'businessName': data['businessName'],
            'businessDescription': data['businessDescription']
        })

        print(f"Business info saved for {user_email}")
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error saving business info: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500






@main.route('/close_onboarding')
def close_onboarding():
    # Clear session and redirect to login
    session.clear()
    return redirect(url_for('main.index'))




@main.route('/complete_onboarding', methods=['POST'])
def complete_onboarding():
    try:
        data = request.get_json()
        print(f"Received onboarding data: {data}")  # Print statement for debugging

        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

        # Reference to the users collection in Firestore
        users_ref = db.collection('users')

        # Update the user document in Firestore
        users_ref.document(user_email).set(data, merge=True)
        users_ref.document(user_email).update({'onboarding_completed': True})

        if 'credentials' in session and session['credentials']:
            session['logged_in'] = True
            session['credentials'] = credentials_to_dict(google_credentials.Credentials(**session['credentials']))
        else:
            return jsonify({'status': 'error', 'message': 'Credentials not found in session'}), 401

        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error in complete_onboarding: {e}")  # Print statement for debugging
        return jsonify({'status': 'error', 'message': str(e)}), 500



@main.route('/abandon_onboarding')
def abandon_onboarding():
    user_email = session.get('user_email')
    if user_email:
        user_doc = db.collection('users').document(user_email).get()
        if user_doc.exists and not user_doc.to_dict().get('onboarding_completed', False):
            db.collection('users').document(user_email).delete()
            flash('Onboarding not completed. User record deleted.', 'info')
    return redirect(url_for('auth.logout'))





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