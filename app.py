##app.py


import json
import re
from dotenv import load_dotenv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric, FilterExpression, Filter, NumericValue
from googleapiclient.discovery import build
import os
import openai
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
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def summarize_ga_data(combined_data):
        summary = {}

        # Example: Extracting total sessions and average session duration
        total_sessions = sum(int(row["sessions"]) for row in combined_data["rows"] if "sessions" in row)
        total_users = sum(int(row["totalUsers"]) for row in combined_data["rows"] if "totalUsers" in row)
        avg_session_duration = sum(float(row["averageSessionDuration"]) for row in combined_data["rows"] if "averageSessionDuration" in row) / len(combined_data["rows"])

        # Example: Identifying top traffic sources
        traffic_sources = {}
        for row in combined_data["rows"]:
            if "sessionSourceMedium" in row and "sessions" in row:
                source = row["sessionSourceMedium"]
                sessions = int(row["sessions"])
                traffic_sources[source] = traffic_sources.get(source, 0) + sessions
        top_traffic_sources = sorted(traffic_sources.items(), key=lambda x: x[1], reverse=True)[:3]

        # Building a summary string
        summary_str = (f"Total Sessions: {total_sessions}, "
                    f"Total Users: {total_users}, "
                    f"Average Session Duration: {avg_session_duration:.2f} seconds. "
                    f"Top Traffic Sources: {', '.join([source for source, _ in top_traffic_sources])}.")
        
        return summary_str


@app.route('/')
def index():
    if 'credentials' not in session:
        # If the user is not logged in, show the login page
        return render_template('login.html')
    elif 'properties' not in session or 'selected_property' not in session:
        # If the user is logged in but hasn't selected a property, show property selection
        return render_template('select_property.html')
    else:
        # If the user has selected a property, show the report
        return render_template('report.html')



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
    return redirect(url_for('index'))


@app.route('/fetch-data', methods=['POST'])

# 3. & 4. Add Data to Chroma Collection (After processing your Google Analytics data)
def fetch_data():
    property_id = request.form['property_id']
    property_type = "GA4" if "UA-" not in property_id else "UA"

    # Set the selected property in the session
    session['selected_property'] = property_id

    credentials = google_credentials.Credentials(**session['credentials'])

    if property_type == "GA4":
        numeric_property_id = property_id.split('/')[-1]
        client = BetaAnalyticsDataClient(credentials=credentials)

        # Define the dimensions and metrics for each batch
        # Batch 1: Traffic and Performance
        batch_1_dimensions = [
            Dimension(name="sessionSourceMedium"),
            Dimension(name="sessionCampaignId"),
            Dimension(name="deviceCategory"),
            Dimension(name="eventName"),
        ]
        batch_1_metrics = [
            Metric(name="sessions"),
            Metric(name="engagedSessions"),
            Metric(name="averageSessionDuration"),
            Metric(name="newUsers"),
            Metric(name="totalUsers"),
            Metric(name="purchaseRevenue"),
            Metric(name="transactions"),
        ]

        # Batch 2: Events Detail
        batch_2_dimensions = [
            Dimension(name="deviceCategory"),
            Dimension(name="linkUrl"),
            Dimension(name="pagePath"),
            Dimension(name="eventName"),
        ]
        batch_2_metrics = [
            Metric(name="addToCarts"),
            Metric(name="checkouts"),
            Metric(name="ecommercePurchases"),
            Metric(name="itemListViews"),
            Metric(name="itemListClicks"),
            Metric(name="itemViews"),
            Metric(name="purchaseRevenue"),
            Metric(name="totalRevenue"),
        ]

        # Batch 3: Page Performance
        batch_3_dimensions = [
            Dimension(name="fullPageUrl"),
            Dimension(name="eventName"),
        ]
        batch_3_metrics = [
            Metric(name="screenPageViews"),
            Metric(name="totalUsers"),
            Metric(name="userEngagementDuration"),
            Metric(name="engagedSessions"),
        ]

        # Batch 4: E-commerce
        batch_4_dimensions = [
            Dimension(name="transactionId"),
            Dimension(name="sessionDefaultChannelGrouping")
        ]
        batch_4_metrics = [
            Metric(name="purchaseRevenue"),
            Metric(name="transactions"),
            Metric(name="totalRevenue"),
            Metric(name="checkouts"),
            Metric(name="addToCarts"),
            Metric(name="ecommercePurchases")
        ]

        # Function to process and combine responses
        def process_response(response, combined_data):
            combined_data["dimension_headers"].extend([dh.name for dh in response.dimension_headers])
            combined_data["metric_headers"].extend([mh.name for mh in response.metric_headers])
            for row in response.rows:
                row_dict = {dh: dv.value for dh, dv in zip(combined_data["dimension_headers"], row.dimension_values)}
                row_dict.update({mh: mv.value for mh, mv in zip(combined_data["metric_headers"], row.metric_values)})
                combined_data["rows"].append(row_dict)

                combined_data["rows"].extend([
                {
                    "dimensions": [dv.value for dv in row.dimension_values],
                    "metrics": [mv.value for mv in row.metric_values]
                } for row in response.rows
            ])

        # Combined response data
        combined_response_data = {
            "dimension_headers": [],
            "metric_headers": [],
            "rows": []
        }

        # Batch 1 request
        ga4_request_1 = RunReportRequest(
            property=f"properties/{numeric_property_id}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            dimensions=batch_1_dimensions,
            metrics=batch_1_metrics
        )
        response_1 = client.run_report(ga4_request_1)
        process_response(response_1, combined_response_data)

        # Batch 2 request
        ga4_request_2 = RunReportRequest(
            property=f"properties/{numeric_property_id}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            dimensions=batch_2_dimensions,
            metrics=batch_2_metrics
        )
        response_2 = client.run_report(ga4_request_2)
        process_response(response_2, combined_response_data)

        # Batch 3 request
        ga4_request_3 = RunReportRequest(
            property=f"properties/{numeric_property_id}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            dimensions=batch_3_dimensions,
            metrics=batch_3_metrics
        )

        # Batch 4 request
        ga4_request_4 = RunReportRequest(
            property=f"properties/{numeric_property_id}",
            date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
            dimensions=batch_4_dimensions,
            metrics=batch_4_metrics
        )
        response_4 = client.run_report(ga4_request_4)
        process_response(response_4, combined_response_data)

        # Convert the Google Analytics data to a string format
        ga_data_string = json.dumps(combined_response_data)

         # New step: Summarize the Google Analytics data
        summarized_data = summarize_ga_data(combined_response_data)  # Implement this function

        # Prepare a single prompt for all tasks in the specified format
        prompt = (f"Analyze this summarized data: {summarized_data}\n\n"
          "### Summary:\n"
          "Provide a concise 3-4 sentence summary. Avoid using a list format.\n"
          "### Key Insights:\n"
          "Generate 4 key insights. Each insight should include: a one-word title, a numeric data point or one word metric (only list the number or one word, dont do '1.39 sessions/user', do '1.39'. Dont do '0.94 seconds', do '0.94s'. We need this to be as short as possible), and one brief explanatory comment no more than 90 characters. Format each insight as a single bullet point. Follow this strict example: 'Traffic - 21.5k - Consistent growth in site visits', 'Source - Organic - Google is a key organic traffic driver.'\n"
          "### Actionable Strategies:\n"
          "Suggest 4 actionable strategies based on the data, 1-2 sentences each, using corresponding emojis as bullet points. Here is a format examples: '- Investigate the cause of the low average session duration to understand if it's due to technical issues or content relevance.', '- Enhance SEO and content strategy to leverage Google as a significant organic traffic driver.'")


        ## OpenAI API call with the new prompt
        response = openai_client.chat.completions.create(
            model="gpt-4-1106-preview",
            temperature=1,
            messages=[
                {"role": "system", "content": "You are a professional analytics assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300  # Adjust as needed
        )

        # Print the AI response in the terminal for debugging
        print("OpenAI Response:", response.choices[0].message.content)
        
        
        # Directly use the plain text response
        insights_text = response.choices[0].message.content
        session['insights'] = insights_text  # Save insights in the session

        return redirect(url_for('show_report'))  # Redirect to a new route



 
@app.route('/report')
def show_report():
    if 'insights' in session:
        insights = session['insights']
        summary = extract_section(insights, "Summary")
        key_insights_raw = extract_section(insights, "Key Insights")
        actionable_strategies_raw = extract_section(insights, "Actionable Strategies")

        key_insights = format_insights(key_insights_raw) if key_insights_raw else []
        actionable_strategies = format_strategies(actionable_strategies_raw) if actionable_strategies_raw else []

        return render_template('report.html', summary=summary, key_insights=key_insights, actionable_strategies=actionable_strategies)
    return redirect(url_for('index'))




def extract_section(text, section_title):
    start_pattern = f"### {section_title}:\n"
    end_pattern = "\n###"

    start_idx = text.find(start_pattern)
    if start_idx == -1:
        return ""  # Return an empty string if section is not found
    start_idx += len(start_pattern)

    end_idx = text.find(end_pattern, start_idx)
    if end_idx == -1:
        end_idx = len(text)

    extracted_text = text[start_idx:end_idx].strip()
    return extracted_text


def format_insights(text):
    insights_list = []
    insights = text.split('\n')
    for insight in insights:
        if insight.strip().startswith('-'):
            insight = insight.lstrip('- ').strip()
            # Split using both dash and colon as possible separators
            parts = re.split(r' - |: ', insight)
            if len(parts) >= 3:
                # Remove double asterisks from both the title and comment
                title = parts[0].replace('**', '').strip()
                data = parts[1]
                comment = parts[2].replace('**', '').strip()
                insight_dict = {
                    'title': title,
                    'data': data,
                    'comment': comment
                }
                insights_list.append(insight_dict)
    return insights_list








def format_strategies(text):
    strategies = text.split('\n')
    formatted_strategies = []
    for strategy in strategies:
        if strategy.strip().startswith('-'):
            # Remove the leading dash and extra space
            strategy = strategy.lstrip('-').strip()

            # Split the strategy text from the emoji
            parts = re.split(r'\s+', strategy, maxsplit=1)
            if len(parts) == 2:
                emoji = parts[0]
                strategy_text = parts[1]
                formatted_strategies.append({'emoji': emoji, 'text': strategy_text})
    return formatted_strategies







def format_paragraph(text):
    paragraphs = text.split('\n')
    return '<br>'.join(p.strip() for p in paragraphs if p.strip())




@app.route('/logout')
def logout():
    # Clear session data
    session.pop('credentials', None)
    session.pop('properties', None)
    session.pop('selected_property', None)
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
