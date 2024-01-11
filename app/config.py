from dotenv import load_dotenv
import os
import openai

# Load environment variables
load_dotenv()

# Shared configurations
CLIENT_SECRETS_FILE = os.environ.get("GOOGLE_CLIENT_SECRETS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FLASK_APP_SECRET_KEY = os.getenv('FLASK_APP_SECRET_KEY')

# OpenAI Client
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
