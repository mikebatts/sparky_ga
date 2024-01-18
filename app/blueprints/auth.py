from flask import Blueprint, session, redirect, url_for, request, flash, current_app
import google_auth_oauthlib.flow
from app.utils import credentials_to_dict, is_credentials_valid
from app.config import CLIENT_SECRETS_FILE
from google.oauth2 import credentials as google_credentials
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests
from google.analytics.admin import AnalyticsAdminServiceClient
from google.analytics.admin_v1alpha.types import ListAccountSummariesRequest
from googleapiclient.discovery import build  # Import statement added
import os

from app.database import db  # Import the Firestore client
auth = Blueprint('auth', __name__, url_prefix='/auth')



@auth.route('/authorize')
def authorize():
    # Clear existing session data
    session.clear()

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=['openid', 'https://www.googleapis.com/auth/analytics.readonly', 'https://www.googleapis.com/auth/userinfo.email'])

    flow.redirect_uri = url_for('auth.oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)

@auth.route('/oauth2callback')
def oauth2callback():
    properties_list = []  # Initialize inside the function
    state = session['state']
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, 
        scopes=['openid', 'https://www.googleapis.com/auth/analytics.readonly', 'https://www.googleapis.com/auth/userinfo.email'], 
        state=state)
    flow.redirect_uri = url_for('auth.oauth2callback', _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials

    # Verify and decode the ID token
    try:
        id_info = google_id_token.verify_oauth2_token(credentials.id_token, requests.Request())
        user_email = id_info['email']
        session['user_email'] = user_email  # Store user email in session

        # Get a reference to the users collection in Firestore
        user_doc = db.collection('users').document(user_email).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            session['user_avatar'] = user_data.get('avatar', url_for('static', filename='default-avatar.png'))  # default avatar if none is set
        else:
            # Set up a new user or handle it as needed
            pass
    except ValueError:
        # Invalid token
        flash('Invalid token. Please try again.')
        return redirect(url_for('main.index'))

    # Check if credentials is a valid object and has an id_token attribute
    # if credentials and hasattr(credentials, 'id_token'):
    #     # Get user's email from credentials
    #     user_email = credentials.id_token['email']
    #     # Rest of your code...
    # else:
    #     flash('Failed to fetch user credentials. Please try again.')
    #     return redirect(url_for('main.index'))

    # Get user's email from credentials
    # user_email = credentials.id_token['email']

    # Get a reference to the users collection in Firestore
    users_ref = db.collection('users')

    # Try to get a document in the users collection with the same ID as the user's email
    doc = users_ref.document(user_email).get()

     # After successfully fetching user email and other details
    user_email = session['user_email']
    user_doc = db.collection('users').document(user_email).get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        session['user_avatar'] = user_data.get('avatar', url_for('static', filename='default-avatar.png'))  # default avatar if none is set

    if not doc.exists:
        users_ref.document(user_email).set({
            'email': user_email  # You can add more placeholder keys if necessary
        })
        return redirect(url_for('main.onboarding'))


    analytics = build('analytics', 'v3', credentials=credentials)

    # Fetch UA properties

    # accounts = analytics.management().accounts().list().execute()
    # properties_list = []
    # if accounts.get('items'):
    #     for account in accounts.get('items'):
    #         account_id = account['id']
    #         properties = analytics.management().webproperties().list(accountId=account_id).execute()
    #         if properties.get('items'):
    #             for property in properties.get('items'):
    #                 profiles = analytics.management().profiles().list(accountId=account_id, webPropertyId=property['id']).execute()
    #                 if profiles.get('items'):
    #                     for profile in profiles.get('items'):
    #                         properties_list.append({
    #                             'account_id': account_id,
    #                             'property_id': property['id'],
    #                             'property_name': property['name'],
    #                             'view_id': profile['id'],
    #                             'property_type': 'UA'
    #                         })

      # Create an Admin API client
    admin_client = AnalyticsAdminServiceClient(credentials=credentials)

    # List GA4 properties
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
                print(properties_list)  # Add this line

    except Exception as e:
        print(f"Error fetching GA4 properties: {e}")

    session['credentials'] = credentials_to_dict(credentials)
    session['properties'] = properties_list
    print("User has been authenticated successfully")

    # Force session to update
    session.modified = True
    current_app.logger.info(f"Properties stored in session: {session['properties']}")

    return redirect(url_for('main.index'))


@auth.route('/logout')
def logout():
    # Clear session data
    session.pop('credentials', None)
    session.pop('properties', None)
    session.pop('selected_property', None)
    print("User has been logged out")
    return redirect(url_for('main.index'))
