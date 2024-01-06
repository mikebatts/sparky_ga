##app.py


import json
from dotenv import load_dotenv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric, FilterExpression, Filter, NumericValue
from googleapiclient.discovery import build
import os

from langchain.output_parsers.pydantic import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.callbacks import StdOutCallbackHandler


from langchain.globals import set_debug, set_verbose
from langchain_community.chat_models import ChatOpenAI


from flask import Flask, jsonify, render_template, redirect, url_for, session, request
import google_auth_oauthlib.flow
from google.oauth2 import credentials as google_credentials

from google.analytics.admin import AnalyticsAdminServiceClient
from google.analytics.admin_v1alpha.types import ListAccountSummariesRequest


from pydantic import BaseModel

class SummaryModel(BaseModel):
    summary: str

class InsightsModel(BaseModel):
    insights: list[str]

class StrategiesModel(BaseModel):
    strategies: list[str]


# LangChainService Class
class LangChainService:
    def __init__(self, api_key):

        if not isinstance(api_key, str):
            raise ValueError("API key must be a string")
        

        self.llm = ChatOpenAI(api_key=api_key, model_name="gpt-4-1106-preview", temperature=0.7, max_tokens=250)
        self.summary_template = "Provide a comprehensive, insightful summary on the performance from this Google Analytics data."
        self.insights_template = "Identify 4 key insights using percentage or numerical metrics from this Google Analytics data."
        self.strategies_template = "Suggest 4 actionable strategies for user improvement based on this Google Analytics data."
        self.summary_chain = self.create_chain_for_template(self.summary_template, SummaryModel)
        self.insights_chain = self.create_chain_for_template(self.insights_template, InsightsModel)
        self.strategies_chain = self.create_chain_for_template(self.strategies_template, StrategiesModel)



    def create_chain_for_template(self, template, output_model):
        prompt_template = PromptTemplate(input_variables=["ga_data"], template=template)
        output_parser = PydanticOutputParser(pydantic_object=output_model)  # Adjusted line
        return LLMChain(llm=self.llm, prompt=prompt_template, output_parser=output_parser)


    def generate_insights(self, ga_data):
        summary = self.summary_chain.predict({"ga_data": ga_data}).summary
        insights = self.insights_chain.predict({"ga_data": ga_data}).insights
        strategies = self.strategies_chain.predict({"ga_data": ga_data}).strategies
        return summary, insights, strategies




##App#########

app = Flask(__name__)
# Load environment variables from .env file
load_dotenv()
app.secret_key = os.getenv('FLASK_APP_SECRET_KEY')

# Replace with the actual path to your client_secret.json
CLIENT_SECRETS_FILE = os.environ.get("GOOGLE_CLIENT_SECRETS")

# Initialize LangChainService with API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

lang_chain_service = LangChainService(api_key)

# Define a function to split text into chunks
def split_text(text, max_length=2000):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


def llm_chain_predict(template, data_chunk):
    prompt_template = PromptTemplate(input_variables=["ga_data_chunk"], template=template)
    llm_chain = LLMChain(llm=lang_chain_service.llm, prompt=prompt_template)
    return llm_chain.predict(ga_data_chunk=data_chunk).strip()


##Routes###############

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

# 3. & 4. Add Data to Chroma Collection (After processing your Google Analytics data)
def fetch_data():
    set_debug(True)
    set_verbose(True)
    property_id = request.form['property_id']
    property_type = "GA4" if "UA-" not in property_id else "UA"
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

        # Use LangChainService for generating insights
        summary, insights, strategies = lang_chain_service.generate_insights(ga_data_string)

        return jsonify({
            'summary': summary,
            'key_insights': insights,
            'actionable_strategies': strategies
        })
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
