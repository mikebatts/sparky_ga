# main.py

from flask import Blueprint, render_template, session, redirect, url_for, flash
from google.oauth2 import credentials as google_credentials
from app.utils import is_credentials_valid

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