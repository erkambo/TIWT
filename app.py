import os
import pathlib
import datetime
import requests
import openai
import re
import sqlite3
#from openai import OpenAI
from flask import Flask, session, abort, redirect, request, render_template, jsonify
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv() #loads env variables

app = Flask("Google Login App")
app.secret_key = os.getenv('SECRET_KEY')
openai.api_key = os.getenv('GPTAPI_KEY')

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" # to allow Http traffic for local dev

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
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

#Database
con = sqlite3.connect("events.db" ,check_same_thread=False) #Con represents connection to database

#We need a cursor to execute SQL statments
cur = con.cursor()

# cur.execute("""
#             CREATE TABLE routines(
#                 title text,
#                 description text,
#                 start text,
#                 end text
#             ) """)

# print("done.")

# cur.execute("""
#             CREATE TABLE goals(
#                 goal text,
#                 description text,
#                 end date text
#                 )
#             """)

# print("done x2")




def getcreds():
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
            
def main():
    
    creds = user.creds
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
        
def parsing_events(initial_response):
    #Splitting response into individual day entries:
    day_entries = initial_response.split("Day ")
    
    for entry in day_entries[1:]:
        #Extract day number
        day_number = entry.split(":")[0].strip()
        
        #extract summary
        
        summary_match = re.search(r'summary: ([^\n]+)', entry) #includes else condition so it at least shows something
        summary = summary_match.group(0) if summary_match else f"Day {day_number}"
                                  
        # Extract description
        description_match = re.search(r'description: ([^\n]+)', entry)
        description = description_match.group(1).strip() if description_match else "No Description included"
        
        color_id = 6
        
        #Start datetime:
        start_match = re.search(r'start: { dateTime: ([^,]+), timeZone: ([^}]+) }', entry)
        start_datetime = start_match.group(1).strip() if start_match else None
        start_timezone = start_match.group(2).strip() if start_match else "America/New_York"
        
        # Extract end datetime
        end_match = re.search(r'end: { dateTime: ([^,]+), timeZone: ([^}]+) }', entry)
        end_datetime = end_match.group(1).strip() if end_match else None
        end_timezone = end_match.group(2).strip() if end_match else "America/New_York"
        
        # Create the event
        event = {
            "summary": summary,
            "description": description,
            "colorId": color_id,
            "start": {
                "dateTime": start_datetime,
                "timeZone": start_timezone,
            },
            "end": {
                "dateTime": end_datetime,
                "timeZone": end_timezone,
            }
        }
        eventcreation(event)
        
def eventcreation(gptevent):
    creds = user.creds
    service = build("calendar", "v3", credentials=creds)
    
    event = gptevent
    
    cur.execute("INSERT INTO routines (title, description, start, end) VALUES (?, ?, ?, ?)",
                (event["summary"], event["description"], event["start"].get("dateTime", event["start"].get("date")),
                 event["end"].get("dateTime", event["end"].get("date"))))
    event = service.events().insert(calendarId="primary", body=event).execute()
    
    # Commit command
    con.commit()

    print(f"Event Created {event.get('htmlLink')}")
    
   
        


    
def ask_gpt(prompt, model="gpt-4o-mini"):
    detailed_prompt = prompt + " , Using the text before here, I want you to start creating a routine for the user depending on how many days they specify. Return your answer in the format Example: summary: Day 1: Learn Multiplication in 10 days description: Start learning your twos (add much more detail here this is just an example) colorID: 6 start:{ dateTime:2024-07-31T19:00:00, timeZone: America/New_York, } end:{ dateTime:2024-07-31T23, timeZone: America/New_York) The events need to start from tomorrow and go on for the amount requested creating events for each day. Do not add any other information or confirmation. Todays date is 2024-08-02"
    
    messages = [{"role": "user", "content": detailed_prompt}]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message["content"]





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
    session["email"] = id_info.get("email")
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
    getcreds()
    allGoals = list(con.execute (f"SELECT rowid, * FROM goals WHERE email = '{session['email']}'"))
    tupleList = []
    for goal in allGoals:
        tupleList.append(goal[1])
        
    else:
        return render_template("goals.html",names = session['name'], email = session['email'], goals = list(tupleList))

@app.route("/calendar", methods = ["GET","POST"])
def calendar():
    eventlist = main()
    return render_template("calendar.html", calendarlist = list(eventlist.values()))

@app.route("/processingevent",methods=["GET","POST"])
def processingevent():
    
    if 'delete' in request.form:
        goal_to_delete = request.form['delete']
        cur.execute("DELETE FROM goals WHERE goal = ?", (goal_to_delete,))
        con.commit()
        return redirect("/goals")
    
    else:
        user_input = request.form['goal']
        
        chatgpt_response = ask_gpt(user_input)
        parsing_events(chatgpt_response)
        # eventcreation()
        return redirect("/goals")


@app.route("/setgoal", methods=["GET","POST"])
def setgoal():
    user_input = request.form['goalcreation']
    details = request.form['details']
    enddate = request.form['date']
    
    cur.execute("INSERT INTO goals (goal, description,end,email) VALUES (?, ?, ?, ?)",
                (user_input,  details, enddate, session['email']))
    con.commit()
    
    return render_template("eventcreated.html", goal = user_input,details = details, date = enddate )
    
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
    
    

    
#close connection
    cur.close()


#CODE