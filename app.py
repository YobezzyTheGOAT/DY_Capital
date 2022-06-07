import os
import requests

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
from datetime import datetime
import psycopg2

from helpers import login_required, getinfo, usd, build_summaries, check_password, getnews

#loading environment
def configure():
    load_dotenv()


# Configure application
app = Flask(__name__)

#secret keys
APIKey = os.getenv('APIkey')
password = os.getenv('password')

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Connect to Postgres database
database = psycopg2.connect(database="dd7ltg9ah7hqh2", user="diijiqsuzbdmae", password=password, host="ec2-34-231-221-151.compute-1.amazonaws.com", port="5432")
commandline = database.cursor()

#Global variable to track login status
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

    global logged

    # retrive API key from environment 
    configure()

    # check if API request for news is successfull
    result = getnews()

    # check if news database exits
    commandline.execute("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename  = 'oldnews')")
    oldnews_exists = commandline.fetchall()

    #retrive news if the database exists
    if oldnews_exists[0][0]:
        commandline.execute("SELECT * FROM oldnews")
        displaynews = commandline.fetchall()


    # redirect to Portfolio page, if API is down
    if result != 1:
        if not oldnews_exists[0][0]:
            flash("API down! Can't retrive news stories")
            return redirect("/portfolio")
        else:
            if logged:
                return render_template("newsloggedin.html", display=displaynews)
            else:
                return render_template("news.html", display=displaynews)
    if result == 1:
        if logged:
            return render_template("newsloggedin.html", display=displaynews)
        else:
            return render_template("news.html", display=displaynews)



@app.route("/portfolio")
@login_required
def portfolio():
    """Show portfolio of stocks"""

    # Check if the user has made any trades
    commandline.execute("SELECT * FROM transactions WHERE theuser = (%s)", (session["user_id"],))
    been_trading = commandline.fetchall()

    if len(been_trading) > 0:
        # Prepare data for casting onto the html page
        commandline.execute("SELECT * FROM summaries WHERE me = (%s)  AND shares > 0", (session["user_id"],))
        data = commandline.fetchall()

               # total_for_all_companies 
        commandline.execute("SELECT SUM(total) FROM summaries WHERE me = (%s)", (session["user_id"],))
        total_for_all_companies = commandline.fetchall()

              # current cash
        commandline.execute("SELECT cash FROM users WHERE id = (%s)", (session["user_id"],))
        current_cash = commandline.fetchall()

        the_total = (total_for_all_companies[0][0] + current_cash[0][0])

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

        return render_template("portfolio.html", data=data, cash=usd(current_cash[0][0]), total=usd(the_total), display=display)

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

        #available cash
        commandline.execute("SELECT cash FROM users WHERE id = (%s)", (session["user_id"],))
        available_cash = commandline.fetchall()

        time = datetime.now()
        cash_balance = (float(available_cash[0][0]) - float(total_cost))

        # Ensure user can afford the purchase
        if not (float(available_cash[0][0]) > float(total_cost)):
            flash("you don't have enough cash!")
            return render_template("buy.html")

        # Effect the purchase
        commandline.execute("INSERT INTO transactions (theuser, company, symbol, type, price, shares, total, timing, dollarprice) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                   (session["user_id"], quotation["name"], quotation["sign"], "BUY", float(the_price), int(shares), float(total_cost), time, usd(float(the_price))))
        database.commit()

        # Update the old primary database
        commandline.execute("UPDATE users SET cash = (%s) WHERE id = (%s)", (cash_balance, session["user_id"]))
        database.commit()

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
    commandline.execute("SELECT * FROM transactions WHERE theuser = (%s)", (session["user_id"],))
    been_trading = commandline.fetchall()

    if len(been_trading) > 0:
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
        commandline.execute("SELECT * FROM users WHERE username = (%s)", (request.form.get("username"),))
        rows = commandline.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            flash("invalid username and/or password!")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0][0]
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

        #exists
        commandline.execute("SELECT username FROM users WHERE username = (%s)", (entered_username,))
        exists = commandline.fetchall()

        # Ensure username was submitted
        if not entered_username:
            flash("please be sure to enter username!")
            return render_template("register.html")

        # Ensure username not already taken up in the database
        elif len(exists) > 0:
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
        commandline.execute("INSERT INTO users (username, hash) VALUES (%s, %s)", (entered_username, hashed_password))
        database.commit()

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

        #shares available for sale
        commandline.execute(
            "SELECT SUM(shares) FROM transactions WHERE theuser = (%s) AND symbol = (%s)", (session["user_id"], company))
        shares_available_forsale = commandline.fetchall()
        
        sales_proceeds = (float(the_price) * float(shares))
        
        #current cash
        commandline.execute("SELECT cash FROM users WHERE id = (%s)", (session["user_id"],))
        current_cash = commandline.fetchall()

        time = datetime.now()

        cash_balance = (float(current_cash[0][0]) + float(sales_proceeds))

        # Ensure user has the shares
        if not (int(shares_available_forsale[0][0]) >= int(shares)):
            flash("you don't have enough shares to sell")
            return redirect("/sell")

        # Effect the sale
        commandline.execute("INSERT INTO transactions (theuser, company, symbol, type, price, shares, total, timing, dollarprice) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                   (session["user_id"], quotation["name"], quotation["sign"], "SELL", float(the_price), (int(shares) * -1), float(sales_proceeds), time, usd(float(the_price))))
        database.commit()

        # Update the old primary database
        commandline.execute("UPDATE users SET cash = (%s) WHERE id = (%s)", (cash_balance, session["user_id"]))
        database.commit

        # Show updated portfolio
        result = build_summaries()

        if result != 1:
            flash("share(s) sold successfully but error in updating Portfolio... please wait and refresh!")
            return redirect("/portfolio")


        flash("share(s) sold successfully!")

        return redirect("/portfolio")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        #symbols
        commandline.execute("SELECT DISTINCT symbol FROM summaries WHERE me = (%s) AND shares > 0", (session["user_id"],))
        symbols = commandline.fetchall()

        return render_template("sell.html", signs=symbols)
