import flask,requests,google, oauthlib
from oauthlib.oauth2 import WebApplicationClient
import os

from flask import Flask, url_for, render_template, redirect

from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
app = Flask(__name__)


# Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

# OAuth 2 client setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

@app.route("/") #Home page
def home():
    return render_template("menu.html")

@app.route("/goals") #goal setting
def goals():
    return render_template("goals.html")

@app.route("/login") #google login
def login():

@app.route("/logout") #google logout
def logout():

@app.route("/login/callback") #google callback
def callback():