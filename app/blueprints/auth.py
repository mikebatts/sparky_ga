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
    session['initiating_login'] = True  # Set the flag when the login process is initiated


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
    state = session['state']
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, 
        scopes=['openid', 'https://www.googleapis.com/auth/analytics.readonly', 'https://www.googleapis.com/auth/userinfo.email'], 
        state=state)
    flow.redirect_uri = url_for('auth.oauth2callback', _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    try:
        id_info = google_id_token.verify_oauth2_token(credentials.id_token, requests.Request())
        user_email = id_info['email']
        session['user_email'] = user_email

        users_ref = db.collection('users')
        user_doc = users_ref.document(user_email).get()

        if session.pop('initiating_login', None):
            if user_doc.exists:
                user_data = user_doc.to_dict()
                session['user_avatar'] = user_data.get('avatar', '')  # Store avatar URL in session
                session['user_business_name'] = user_data.get('businessName', 'Your Business')  # Store business name in session
                redirect_url = url_for('main.select_property')
            else:
                users_ref.document(user_email).set({
                    'email': user_email,
                    'onboarding_completed': False
                })
                redirect_url = url_for('main.onboarding')
        else:
            flash('Login not initiated by the user.')
            redirect_url = url_for('auth.authorize')

    except ValueError:
        flash('Invalid token. Please try again.')
        redirect_url = url_for('auth.authorize')



    # Fetch properties regardless of new or returning user
    try:
        admin_client = AnalyticsAdminServiceClient(credentials=credentials)
        account_summaries = admin_client.list_account_summaries(ListAccountSummariesRequest())
        properties_list = []
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

        session['properties'] = properties_list
    except Exception as e:
        flash(f"Error fetching GA4 properties: {e}", "error")

    return redirect(redirect_url)



@auth.route('/logout')
def logout():
    print("Logging out user:", session.get('user_email', 'Unknown'))
    # Clear session data including the logged_in flag
    session.pop('credentials', None)
    session.pop('properties', None)
    session.pop('selected_property', None)
    session.pop('logged_in', None)  # Clear the logged_in flag
    print("User logged out")
    return redirect(url_for('main.index'))


