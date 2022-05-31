import os
import requests

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv


from datetime import datetime

from helpers import login_required, getinfo, usd, build_summaries, check_password, getnews

#loading environment
def configure():
    load_dotenv()


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///database.db")

# Global variable for tracking user status
logged = False


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """flash news"""

    # retrive API key from environment 
    configure()

    # check if API request for news is successfull
    result = getnews()

    # redirect to Portfolio page, if API is down
    if result != 1:
        flash("API down! Can't retrive news stories")
        return redirect("/portfolio")

    global logged

    newsdatabase_exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name= ?", 'thenews')
    
    if newsdatabase_exists:
        if logged:
            displaynews = db.execute("SELECT * FROM thenews")
            return render_template("newsloggedin.html", display=displaynews)
        else:
            displaynews = db.execute("SELECT * FROM thenews")
            return render_template("news.html", display=displaynews)
            
  
    # Redirect user to home page
    return redirect("/portfolio")


@app.route("/portfolio")
@login_required
def portfolio():
    """Show portfolio of stocks"""
    # Check if the user has made any trades
    been_trading = db.execute("SELECT * FROM transactions WHERE user = ?", session["user_id"])

    if been_trading:
        # Prepare data for casting onto the html page
        data = db.execute("SELECT * FROM summaries WHERE user = ? AND shares > 0", session["user_id"])

        total_for_all_companies = db.execute("SELECT SUM(total) FROM summaries WHERE user = ?", session["user_id"])
        current_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        the_total = (total_for_all_companies[0]['SUM(total)'] + current_cash[0]['cash'])

        original_cash = 10000
        profitloss = the_total - original_cash
        percentage = (profitloss/original_cash) * 100

        display = []
        if profitloss > 0:
            display.append("Profit")
        elif profitloss < 0:
            display.append("Loss")
        else:
            display.append("_")
        
        display.append(profitloss)
        display.append(int(percentage))


        return render_template("portfolio.html", data=data, cash=usd(current_cash[0]['cash']), total=usd(the_total), display=display)

    # Incase the user hasn't made any trades
    else:
        return render_template("emptyportfolio.html")



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        company = request.form.get("symbol")
        shares = request.form.get("shares")
        quotation = getinfo(company)

        # Ensure lookup got results
        if not quotation:
            print("QUOTATION NOT FOUND")
            flash("quotation not found!")
            return render_template("buy.html")

        the_price = quotation["shareprice"]
        total_cost = (float(the_price) * float(shares))
        available_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        time = datetime.now()
        cash_balance = (float(available_cash[0]['cash']) - float(total_cost))

        # Ensure user can afford the purchase
        if not (float(available_cash[0]['cash']) > float(total_cost)):
            flash("you don't have enough cash!")
            return render_template("buy.html")

        # Effect the purchase
        db.execute("INSERT INTO transactions (user, company, symbol, type, price, shares, total, timing, dollarprice) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   session["user_id"], quotation["name"], quotation["sign"], "BUY", float(the_price), int(shares), float(total_cost), time, usd(float(the_price)))

        # Update the old primary database
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_balance, session["user_id"])

        # Show updated portfolio
        result = build_summaries()

        if result != 1:
            flash("share(s) bought successfully but error in updating Portfolio... please wait and refresh!")
            return redirect("/portfolio")

        flash("share(s) bought successfully!")

        return redirect("/portfolio")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Check if the user has made any trades
    been_trading = db.execute("SELECT * FROM transactions WHERE user = ?", session["user_id"])

    if been_trading:
        return render_template("history.html", data=been_trading)

    else:
        return render_template("emptyhistory.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    global logged

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("please be sure to enter username!")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("please be sure to enter password!")
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("invalid username and/or password!")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        logged = True

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    global logged

    # Forget any user_id
    session.clear()
    logged = False

    # Redirect user to login form
    return redirect("/")



@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        entered_symbol = request.form.get("symbol")
        quotation = getinfo(entered_symbol)

        # Ensure lookup got results
        if not quotation:
            flash("quotation not found!")
            return render_template("quote.html")

        # Take user to page displaying quotations
        return render_template("quotation.html", quotation=quotation)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        entered_username = request.form.get("username")
        entered_password = request.form.get("password")
        confirmed_password = request.form.get("confirmation")
        hashed_password = generate_password_hash(entered_password, method='pbkdf2:sha256', salt_length=8)
        exists = db.execute("SELECT username FROM users WHERE username = ?", entered_username)

        # Ensure username was submitted
        if not entered_username:
            flash("please be sure to enter username!")
            return render_template("register.html")

        # Ensure username not already taken up in the database
        elif exists:
            flash("username already taken!")
            return render_template("register.html")

        # Ensure password was submitted
        elif not entered_password:
            flash("please be sure to enter password!")
            return render_template("register.html")

        # Ensure password has atleast 8 characters; including atleast a capital letter, a number, and symbol.
        elif not check_password(entered_password):
            flash("password should have atleast 8 characters; including atleast a capital letter, a number, and symbol")
            return render_template("register.html")

        # Ensure password confirmed correctly
        elif (entered_password != confirmed_password):
            flash("password not confirmed!")
            return render_template("register.html")

        # Record user details
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", entered_username, hashed_password)

        # Take user to login page
        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        company = request.form.get("symbol")
        shares = request.form.get("shares")
        quotation = getinfo(company)

        # Ensure lookup got results
        if not quotation:
            flash("quotation not found!")
            return render_template("sell.html")

        the_price = quotation["shareprice"]
        shares_available_forsale = db.execute(
            "SELECT SUM(shares) FROM transactions WHERE user = ? AND symbol = ?", session["user_id"], company)
        sales_proceeds = (float(the_price) * float(shares))
        current_cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        time = datetime.now()

        cash_balance = (float(current_cash[0]['cash']) + float(sales_proceeds))

        # Ensure user has the shares
        if not (int(shares_available_forsale[0]['SUM(shares)']) >= int(shares)):
            flash("you don't have enough shares to sell")
            return redirect("/sell")

        # Effect the sale
        db.execute("INSERT INTO transactions (user, company, symbol, type, price, shares, total, timing, dollarprice) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   session["user_id"], quotation["name"], quotation["sign"], "SELL", float(the_price), (int(shares) * -1), float(sales_proceeds), time, usd(float(the_price)))

        # Update the old primary database
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash_balance, session["user_id"])

        # Show updated portfolio
        result = build_summaries()

        if result != 1:
            flash("share(s) sold successfully but error in updating Portfolio... please wait and refresh!")
            return redirect("/portfolio")


        flash("share(s) sold successfully!")

        return redirect("/portfolio")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        symbols = db.execute("SELECT DISTINCT symbol FROM summaries WHERE user = ?", session["user_id"])
        return render_template("sell.html", signs=symbols)
