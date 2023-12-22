##app.py

from dotenv import load_dotenv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
from googleapiclient.discovery import build
import os
from flask import Flask, jsonify, render_template, redirect, url_for, session, request
import google_auth_oauthlib.flow
from google.oauth2 import credentials as google_credentials

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_APP_SECRET_KEY')

# Replace with the actual path to your client_secret.json
CLIENT_SECRETS_FILE = os.environ.get("GOOGLE_CLIENT_SECRETS")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/authorize')
def authorize():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=['https://www.googleapis.com/auth/analytics.readonly'])

    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, 
        scopes=['https://www.googleapis.com/auth/analytics.readonly'], 
        state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    analytics = build('analytics', 'v3', credentials=credentials)

    # Fetch UA properties
    accounts = analytics.management().accounts().list().execute()
    properties_list = []
    if accounts.get('items'):
        for account in accounts.get('items'):
            account_id = account['id']
            properties = analytics.management().webproperties().list(accountId=account_id).execute()
            if properties.get('items'):
                for property in properties.get('items'):
                    profiles = analytics.management().profiles().list(accountId=account_id, webPropertyId=property['id']).execute()
                    if profiles.get('items'):
                        for profile in profiles.get('items'):
                            properties_list.append({
                                'account_id': account_id,
                                'property_id': property['id'],
                                'property_name': property['name'],
                                'view_id': profile['id'],
                                'property_type': 'UA'
                            })

    # Fetch GA4 properties using Data API
    data_client = BetaAnalyticsDataClient(credentials=credentials)
    try:
        # Listing all GA4 properties
        ga4_properties = data_client.list_properties()
        for property in ga4_properties.properties:
            properties_list.append({
                'account_id': property.parent.split('/')[-1],
                'property_id': property.name.split('/')[-1],
                'property_name': property.display_name,
                'property_type': 'GA4'
            })
    except Exception as e:
        print(f"Error fetching GA4 properties: {e}")

    session['credentials'] = credentials_to_dict(credentials)
    session['properties'] = properties_list
    print("User has been authenticated successfully")
    return redirect(url_for('index'))


@app.route('/fetch-data', methods=['POST'])
def fetch_data():
    property_id = request.form['property_id']
    property_type = "GA4" if "UA-" not in property_id else "UA"

    credentials = google_credentials.Credentials(**session['credentials'])

    if property_type == "GA4":
        # Handle GA4 property
        client = BetaAnalyticsDataClient(credentials=credentials)
        ga4_request = RunReportRequest(
            property=f"properties/{property_id}",  # Ensure numeric ID is used here
            date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
            dimensions=[Dimension(name="browser")],
            metrics=[Metric(name="activeUsers")]
        )
        response = client.run_report(ga4_request)
        return jsonify(response.to_dict())

    elif property_type == "UA":
        # Find view_id for the selected UA property
        view_id = None
        for prop in session.get('properties', []):  # Renamed variable here
            if prop['property_id'] == property_id and prop['property_type'] == 'UA':
                view_id = prop.get('view_id')

        if not view_id:
            return "No viewId found for UA property.", 400

        # Handle UA property
        analytics = build('analyticsreporting', 'v4', credentials=credentials)
        ua_request_body = {  # Renamed variable here
            'reportRequests': [
                {
                    'viewId': view_id,
                    'dateRanges': [{'startDate': '30daysAgo', 'endDate': 'today'}],
                    'metrics': [
                        # Add as many metrics as required
                        {'expression': 'ga:sessions'},
                        {'expression': 'ga:users'},
                        {'expression': 'ga:newUsers'},
                        # ...
                    ],
                    'dimensions': [
                        # Add as many dimensions as required
                        {'name': 'ga:browser'},
                        {'name': 'ga:country'},
                        {'name': 'ga:city'},
                        # ...
                    ],
                    # Additional request parameters...
                }
            ]
        }
        response = analytics.reports().batchGet(body=ua_request_body).execute()
        return jsonify(response)

    else:
        return "Invalid property type", 400




@app.route('/logout')
def logout():
    # Clear session data
    session.pop('credentials', None)
    session.pop('properties', None)
    print("User has been logged out")
    return redirect(url_for('index'))

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes}

if __name__ == '__main__':
    # When running locally, set 'OAUTHLIB_INSECURE_TRANSPORT' to enable non-HTTPS testing
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for testing on localhost
    app.run('localhost', 8080, debug=True)
