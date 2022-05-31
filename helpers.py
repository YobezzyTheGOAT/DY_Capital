import os
import requests
import urllib.parse
from cs50 import SQL

from flask import redirect, render_template, request, session
from functools import wraps

import re

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///database.db")



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

    summary_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name= ?", 'summaries')

    # Ensure file has been created to store summaries for display
    if not summary_exists:
        db.execute("CREATE TABLE summaries (user INTEGER, symbol TEXT, company TEXT, shares INTEGER, price INTEGER, total INTEGER, dollarprice TEXT, dollartotal TEXT, FOREIGN KEY(user) REFERENCES users(id))")

     # Clear earlier entries if file already exits
    db.execute("DELETE FROM summaries")

    # Pick out the companies whose stocks the user has traded
    company = db.execute("SELECT DISTINCT company FROM transactions WHERE user = ?", session["user_id"])

    # Loop through each company and collect all the info needed for display and insert it into the summaries file
    for dict_item in company:
        for key in dict_item:
            symbol = db.execute("SELECT symbol FROM transactions WHERE company = ?", dict_item[key])
            current_shares = db.execute("SELECT SUM(shares) FROM transactions WHERE company = ? AND user = ?",
                                        dict_item[key], session["user_id"])
            
            try:
                quotation = getinfo(symbol[0]['symbol'])
            except (KeyError, TypeError, ValueError, IndexError):
                return None

            price = quotation["shareprice"]
            total = (current_shares[0]['SUM(shares)'] * float(price))

            db.execute("INSERT INTO summaries (user, symbol, company, shares, price, total, dollarprice, dollartotal) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       session["user_id"], symbol[0]['symbol'], dict_item[key], current_shares[0]['SUM(shares)'], price, total, usd(price), usd(total))


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
        
        newsdatabase_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name= ?", 'thenews')
        
        # Ensure file has been created to store summaries for display
        if not newsdatabase_exists:
            db.execute("CREATE TABLE thenews (title TEXT, link TEXT, source TEXT)")
            
        # Clear earlier entries if file already exits
        db.execute("DELETE FROM thenews")
        
        # insert news into database
        for n in range(0, 8):
            title = data[n]["title"]
            link = data[n]["link"]
            source = data[n]["source"] 
            db.execute("INSERT INTO thenews (title, link, source) VALUES (?, ?, ?)", title, link, source)
            print("ITEM ADDED")
        return 1
    except (KeyError, TypeError, ValueError, IndexError):
        return None

