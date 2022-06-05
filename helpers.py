import os
import requests
import urllib.parse
from cs50 import SQL
import psycopg2

from flask import redirect, render_template, request, session
from functools import wraps

import re

# connect to database
database = psycopg2.connect(database="DYCapital", user="postgres", password=os.getenv("password"), host="localhost", port="5432")
commandline = database.cursor()


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def getinfo(symbol):
    """Look up quote for symbol."""

    # Contact API

    try:
        url = "https://mboum-finance.p.rapidapi.com/qu/quote"
        
        querystring = {"symbol":symbol}

        headers = {"X-RapidAPI-Host": "mboum-finance.p.rapidapi.com",
        "X-RapidAPI-Key": os.getenv("APIkey")
        }
        response = requests.request("GET", url, headers=headers, params=querystring)
        response.raise_for_status
    except requests.RequestException:
        return None

    # Parse response
    try:
        data = response.json()
        return {
        "name" : data[0]["longName"], 
        "sign" :  data[0]["symbol"],  
        "shareprice" : data[0]["regularMarketPrice"],   
        "capitation" : data[0]["marketCap"],  
        "dyield" : data[0]["trailingAnnualDividendYield"],  
        "eps" : data[0]["epsTrailingTwelveMonths"], 
        "futureeps" : data[0]["epsForward"],  
        "bookvalue" : data[0]["bookValue"], 
        "pe" : data[0]["trailingPE"]
        }
    except (KeyError, TypeError, ValueError, IndexError):
        return None



def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def build_summaries():
    """Create summary database for displaying portfolio"""
    
    commandline.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename  = 'summaries')")
    summary_exists = commandline.fetchall()

    # Ensure file has been created to store summaries for display
    if not summary_exists[0][0]:
        commandline.execute("CREATE TABLE summaries (me INTEGER REFERENCES users(id), symbol TEXT, company TEXT, shares INTEGER, price INTEGER, total INTEGER, dollarprice TEXT, dollartotal TEXT)")
        database.commit()

    # Clear earlier entries if file already exits
    commandline.execute("DELETE FROM summaries")
    database.commit()

    # Pick out the companies whose stocks the user has traded
    commandline.execute("SELECT DISTINCT company FROM transactions WHERE theuser = (%s) AND shares > 0", (session["user_id"],))
    company = commandline.fetchall()

    # Loop through each company and collect all the info needed for display and insert it into the summaries file
    for row in company:
        commandline.execute("SELECT symbol FROM transactions WHERE company = (%s)", (row[0],))
        print("symbol =", row[0])
        symbol = commandline.fetchall()

        commandline.execute("SELECT SUM(shares) FROM transactions WHERE company = (%s) AND theuser = (%s)", (row[0], session["user_id"]))
        current_shares = commandline.fetchall()
            
        try:
            quotation = getinfo(symbol[0][0])
        except (KeyError, TypeError, ValueError, IndexError):
            return None

        price = quotation["shareprice"]
        total = (current_shares[0][0] * float(price))

        commandline.execute("INSERT INTO summaries (me, symbol, company, shares, price, total, dollarprice, dollartotal) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                       (session["user_id"], symbol[0][0], row[0], current_shares[0][0], price, total, usd(price), usd(total)))
        database.commit()

    return 1


def check_password(password):
    def caps(password):
        for x in password:
            if x.isupper():
                return True

    def num(password):
        for x in password:
            if x.isnumeric():
                return True

    def length(password):
        if (len(password) >= 8):
            return True

    def special(password):
        special_char = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
        if (special_char.search(password) != None):
            return True

    if (length(password) or caps(password) or num(password) or special(password)):
        return True



def getnews():
    """Retrive news information from the API"""

    try:
        url = "https://mboum-finance.p.rapidapi.com/ne/news"
        
        headers = {"X-RapidAPI-Host": "mboum-finance.p.rapidapi.com",
            "X-RapidAPI-Key": os.getenv("APIkey")
        }
        response = requests.request("GET", url, headers=headers)
        response.raise_for_status
    except requests.RequestException:
        print("DATA NOT FOUND")
        return None

    try:
        data = response.json()
        print("data got successfully")

        commandline.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename  = 'thenews')")
        newsdatabase_exists = commandline.fetchall()

        commandline.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename  = 'oldnews')")
        oldnewsdatabase_exists = commandline.fetchall()
        
        
        # Ensure file has been created to store news for display
        if not newsdatabase_exists[0][0]:
            commandline.execute("CREATE TABLE thenews (title TEXT, link TEXT, source TEXT)")
            database.commit()
        
        if not oldnewsdatabase_exists[0][0]:
            commandline.execute("CREATE TABLE oldnews (title TEXT, link TEXT, source TEXT)")
            database.commit()

            
        # Clear earlier entries if file already exits
        commandline.execute("DELETE FROM thenews")
        database.commit()
        
        # insert news into database
        for n in range(0, 8):
            title = data[n]["title"]
            link = data[n]["link"]
            source = data[n]["source"] 
            commandline.execute("INSERT INTO thenews (title, link, source) VALUES (%s, %s, %s)", (title, link, source))
            database.commit()

        # Clear old news if new news written successfully 
        commandline.execute("DELETE FROM oldnews")
        database.commit()

        # update old news
        for n in range(0, 8):
            title = data[n]["title"]
            link = data[n]["link"]
            source = data[n]["source"] 
            commandline.execute("INSERT INTO oldnews (title, link, source) VALUES (%s, %s, %s)", (title, link, source))
            database.commit()
        return 1
    except (KeyError, TypeError, ValueError, IndexError):
        return None

