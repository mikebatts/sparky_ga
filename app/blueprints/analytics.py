from flask import Blueprint, request, session, redirect, url_for, flash, jsonify
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
from app.utils import is_credentials_valid, summarize_ga_data
from app.config import openai_client
from google.oauth2 import credentials as google_credentials
import json, logging

analytics = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics.route('/fetch-data', methods=['POST'])
def fetch_data():
    try:
        property_id = request.form['property_id']
        property_type = "GA4" if "UA-" not in property_id else "UA"

        # Set the selected property in the session
        session['selected_property'] = property_id

        # Check if credentials are valid
        credentials = google_credentials.Credentials(**session.get('credentials', {}))
        if not is_credentials_valid(credentials):
            flash("Your session has expired. Please log in again.", "error")
            return redirect(url_for('main.index'))

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
            summarized_data = summarize_ga_data(combined_response_data)

            # Prepare a single prompt for all tasks in the specified format
            prompt = (f"Analyze this summarized data: {summarized_data}\n\n"
            "### Summary:\n"
            "Provide a concise 3-4 sentence summary. Avoid using a list format.\n"
            "### Key Insights:\n"
            "Generate 4 key insights. Each insight should include: a one-word title, a numeric data point or one word metric (only list the number or one word, dont do '1.39 sessions/user', do '1.39'. Dont do '0.94 seconds', do '0.94s'. We need this to be as short as possible), and one brief explanatory comment no more than 90 characters. Format each insight as a single bullet point. Follow this strict example: 'Traffic - 21.5k - Consistent growth in site visits', 'Source - Organic - Google is a key organic traffic driver.'\n"
            "### Actionable Strategies:\n"
            "Suggest 4 actionable strategies based on the data, 1-2 sentences each, using corresponding emojis as bullet points. Here is a format examples: '- Investigate the cause of the low average session duration to understand if it's due to technical issues or content relevance.', '- 📈 Enhance SEO and content strategy to leverage Google as a significant organic traffic driver.'")


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

            insights_text = response.choices[0].message.content
            session['insights'] = insights_text

            return redirect(url_for('reports.show_report'))

    except Exception as e:
        logging.error(f"Error in fetch-data: {e}")
        flash("An error occurred while fetching data.", "error")
        return redirect(url_for('main.index'))



        # Print the AI response in the terminal for debugging
        print("OpenAI Response:", response.choices[0].message.content)
        
        
        # Directly use the plain text response
        insights_text = response.choices[0].message.content
        session['insights'] = insights_text  # Save insights in the session

        return redirect(url_for('reports.show_report'))  # Redirect to a new route

        

