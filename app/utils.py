#utils.py

import re
from flask import flash, redirect, url_for, session
from google.oauth2 import credentials as google_credentials

def check_user_session():
    """
    Check if the user is logged in and has valid credentials.
    If not, flash a message and redirect to login.
    """
    if 'credentials' in session:
        credentials = google_credentials.Credentials(**session['credentials'])
        if not credentials.expired and credentials.valid:
            return None  # User is logged in and has valid credentials
    flash("Your session has expired, please sign in again.", "error")
    return redirect(url_for('main.index'))  # Adjust 'main.login' to your login route


def is_credentials_valid(credentials):
    """
    Checks if the provided credentials are valid.
    """
    return credentials and not credentials.expired and credentials.valid
    # return False


def summarize_ga_data(combined_data, user_data):
    # Initial variables for possible data points
    total_sessions = 0
    total_users = 0
    avg_session_duration = 0
    traffic_sources = {}

    # Extract relevant data points from combined_data
    for row in combined_data["rows"]:
        if "sessions" in row:
            total_sessions += int(row["sessions"])
        if "totalUsers" in row:
            total_users += int(row["totalUsers"])
        if "averageSessionDuration" in row:
            avg_session_duration += float(row["averageSessionDuration"])
        if "sessionSourceMedium" in row and "sessions" in row:
            source = row["sessionSourceMedium"]
            sessions = int(row["sessions"])
            traffic_sources[source] = traffic_sources.get(source, 0) + sessions

    # Calculate average session duration if applicable
    if combined_data["rows"]:
        avg_session_duration /= len(combined_data["rows"])

    # Top traffic sources
    top_traffic_sources = sorted(traffic_sources.items(), key=lambda x: x[1], reverse=True)[:3]

    # Building a dynamic summary based on user preferences/goals
    summary_elements = []

    # Example logic to add relevant data points based on user preferences
    if 'engagement' in user_data.get('preferences', []):
        summary_elements.append(f"Average Session Duration: {avg_session_duration:.2f} seconds")

    if 'audience' in user_data.get('preferences', []):
        summary_elements.append(f"Total Users: {total_users}")

    if 'acquisition' in user_data.get('preferences', []):
        summary_elements.append(f"Top Traffic Sources: {', '.join([source for source, _ in top_traffic_sources])}")

    # Combine the elements into a summary string
    summary_str = ', '.join(summary_elements)

    return summary_str



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


def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
