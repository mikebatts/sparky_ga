import os
import flask
import google_auth_oauthlib.flow

app = flask.Flask(__name__)
app.secret_key = 'Sfogliatelle1209!'  # Replace with a strong secret key

# Replace with the actual path to your client_secret.json
CLIENT_SECRETS_FILE = os.environ.get("GOOGLE_CLIENT_SECRETS")

@app.route('/')
def index():
    return flask.render_template('index.html')

@app.route('/authorize')
def authorize():
    # Create an OAuth 2.0 flow object
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=['https://www.googleapis.com/auth/analytics.readonly'])

    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')

    flask.session['state'] = state

    return flask.redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = flask.session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, 
        scopes=['https://www.googleapis.com/auth/analytics.readonly'], 
        state=state)
    flow.redirect_uri = flask.url_for('oauth2callback', _external=True)

    authorization_response = flask.request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    flask.session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes}

    return flask.redirect(flask.url_for('index'))

if __name__ == '__main__':
    # When running locally, set 'OAUTHLIB_INSECURE_TRANSPORT' to enable non-HTTPS testing
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Only for testing on localhost
    app.run('localhost', 8080, debug=True)
