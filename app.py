# app.py

# from app import app

# if __name__ == '__main__':
#     app.run('localhost', 8080, debug=True)

from app import app
import os

if __name__ == '__main__':
    # Use Heroku's PORT environment variable, with a fallback to 8080 if it's not set.
    port = int(os.getenv('PORT', 8080))
    # Bind to 0.0.0.0 to allow access from outside the container.
    app.run(host='0.0.0.0', port=port)
