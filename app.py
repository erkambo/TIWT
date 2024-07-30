import os
import pathlib
import datetime
import requests
from flask import Flask, session, abort, redirect, request, render_template
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask("Google Login App")
app.secret_key = "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" # make sure this matches with that's in client_secret.json

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" # to allow Http traffic for local dev

GOOGLE_CLIENT_ID = "255099809593-78h1jr7mubuto6s7iern9ebdf0l14umk.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid", "https://www.googleapis.com/auth/calendar"],
    redirect_uri="http://127.0.0.1/callback", 
)


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class user:
    creds = None


def main():
    #This section checks for credentials
    creds = None 
    
    if os.path.exists("tokens.json"): #if logged in previously
        user.creds = Credentials.from_authorized_user_file("token.json")
        creds = Credentials.from_authorized_user_file("token.json")
    if not creds or not creds.valid: #if token is invalid or expired
        if creds and creds.expired and creds.refresh_token: 
            creds.refresh(Request)
        else:
            creds = flow.credentials
            user.creds = flow.credentials
        #save the flow for future login
        
        with open("token.json", "w") as token: #write to file token.json
            token.write(creds.to_json())
            
            
    try: #Get a list of events in your calendar
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        print("Getting the upcoming 10 events")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        
        calendarlist = {}
        if not events:
            print("No upcoming events found.") 
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            calendarlist[start] = event["summary"]
        return calendarlist

    except HttpError as error:
        print(f"An error occurred: {error}")
        

def eventcreation():
    creds = user.creds
    service = build("calendar", "v3", credentials = creds)
    
    event = { #basically we need to create a lot of key value pairs
        "summary": "My Python Event",
        "location": "Somewhere Online",
        "description": "This event very very cool like I love it!",
        "colorID": 6,
        "start":{
            "dateTime":"2024-07-31T19:00:00", #datetime includes timestamp T and utc -5
            "timeZone": "America/New_York",
        },
        "end":{
            "dateTime":"2024-07-31T23:00:00", #datetime includes timestamp T and utc -5
            "timeZone": "America/New_York",
        },
        
        "attendees":[
            
            {"email":"boyaciogluerkam@gmail.com"},
            {"email":"erkanbobo33@gmail.com"}
        ]
    
    }
    
    event = service.events().insert(calendarId = "primary",body = event).execute()
    print(f"Event Created {event.get('htmlLink')}")

        

 













def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


#Routing
@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    return redirect("/goals")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/")
def index():
    return render_template("menu.html")


@app.route("/goals")
@login_is_required
def protected_area():
    return render_template("goals.html",names = session['name']) 

@app.route("/calendar")
def calendar():
    eventlist = main()
    return render_template("calendar.html", calendarlist = eventlist)

@app.route("/processingevent",methods=["POST"])
def processingevent():
    eventcreation()
    return "Success"
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
    
    

    



#CODE

