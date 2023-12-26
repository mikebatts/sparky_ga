##app.py

from dotenv import load_dotenv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric, FilterExpression, Filter, NumericValue
from googleapiclient.discovery import build
import os
from flask import Flask, jsonify, render_template, redirect, url_for, session, request
import google_auth_oauthlib.flow
from google.oauth2 import credentials as google_credentials

from google.analytics.admin import AnalyticsAdminServiceClient
from google.analytics.admin_v1alpha.types import ListAccountSummariesRequest

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
    properties_list = []  # Initialize inside the function
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
                properties_list.append({
                    'account_id': account.account,
                    'property_id': property_summary.property,
                    'property_name': property_summary.display_name,
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
        numeric_property_id = property_id.split('/')[-1]

        # Update dimensions and metrics according to your new requirements
        dimensions = [
            Dimension(name="landingPage"),
            Dimension(name="pagePath"),
            Dimension(name="deviceCategory"),
            Dimension(name="deviceModel"),
            Dimension(name="brandingInterest"),
            Dimension(name="region"),
            Dimension(name="cityId")
        ]

        metrics = [
            Metric(name="newUsers"),
            Metric(name="totalUsers"),
            Metric(name="checkouts"),
            Metric(name="scrolledUsers"),
            Metric(name="averageSessionDuration"),
            Metric(name="bounceRate"),
            Metric(name="engagementRate"),
            Metric(name="sessions"),
            Metric(name="conversions"),
            Metric(name="screenPageViews")
        ]

        client = BetaAnalyticsDataClient(credentials=credentials)
        ga4_request = RunReportRequest(
            property=f"properties/{numeric_property_id}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            dimensions=dimensions,
            metrics=metrics,
            # Update or remove filters based on your requirements
        )
        response = client.run_report(ga4_request)

        response_data = {
            "dimension_headers": [dh.name for dh in response.dimension_headers],
            "metric_headers": [mh.name for mh in response.metric_headers],
            "rows": [
                {
                    "dimensions": [dv.value for dv in row.dimension_values],
                    "metrics": [mv.value for mv in row.metric_values]
                }
                for row in response.rows
            ]
        }

        return jsonify(response_data)

    # elif property_type == "UA":
    #     # UA handling code remains unchanged

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
