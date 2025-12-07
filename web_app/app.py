"""
app.py
------
Entry point for the Flask web application. Defines routes for authentication,
event display, reference image upload, and serving captured images. Integrates
backend logic with templates to power the IdentifAI dashboard.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from database import init_db, add_user, verify_user
from auth import login_required

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev'

    init_db()

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)

