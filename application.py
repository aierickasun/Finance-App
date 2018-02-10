from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
import datetime

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    session["stocks"] = []
    stocks = db.execute("SELECT * from stocks WHERE user_id=:user_id", user_id=session["user_id"])
    if stocks:
        session["debug"] = stocks[0]["ticker"]
        session["total"] = 0
        for i in stocks:# [ { }, { }]
            block={}
            stock = lookup(i.get("ticker"))
            flag=False
            for s in session["stocks"]:
                if s["ticker"]==stock["symbol"]:
                    flag=True
                    if i["method"]=="BUY":
                        s["num_shares"] += i["num_shares"]
                   #     session["total"]+=i["price"] * s["num_shares"]
                    else:
                        s["num_shares"] -= i["num_shares"]
                   #     session["total"]-=i["price"] * s["num_shares"]
            if flag==False:
                block["name"] = stock["name"]
                block["ticker"] = stock["symbol"]
                block["price"] = stock["price"]
                if i["method"]=="BUY":
                    block["num_shares"] = i["num_shares"]
                  #  session["total"]+=block["price"] * block["num_shares"]
                else:
                    block["num_shares"] = i["num_shares"] * (-1)
                 #   session["total"]-=block["price"] * i["num_shares"]
                session["stocks"].append(block)
                
        user_balance = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
        user_balance = user_balance[0]["cash"]
        session["balance"] = user_balance
    return render_template("index.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    user_balance = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
    user_balance = user_balance[0]["cash"]
    session["balance"] = user_balance
    if request.method == "POST":
        #Display current balance, etc.
        num_shares = request.form.get("shares_num")
        if not request.form.get("ticker_symbol"):
            return apology("Need a ticker symbol")
        if not request.form.get("shares_num"):
            return apology("Number of shares not given")
        if not num_shares.isdigit():
            return apology("Input for number of shares must be a number")
        num_shares = int(num_shares)
        sym = request.form.get("ticker_symbol")
        sym_lookup = lookup(sym)
        if not sym_lookup:
            return apology("Could not find symbol")
        
        if not (user_balance - (num_shares*sym_lookup["price"]) > 0):
            return apology("Insufficient funds")
        #EXECUTE BUY!
        db.execute("INSERT INTO stocks (user_id, ticker, num_shares,method,price,date) VALUES(:user_id, :ticker, :num_shares,:method,:price,:date)", user_id=session["user_id"], ticker=sym_lookup["symbol"], num_shares=num_shares, method="BUY", price=sym_lookup["price"], date=str(datetime.datetime.now()))
        db.execute("UPDATE users SET cash=:cash WHERE id=:user_id", cash=user_balance - (num_shares*sym_lookup["price"]), user_id=session["user_id"])
        
    user_balance = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
    user_balance = user_balance[0]["cash"]
    session["balance"] = user_balance
    return render_template("buy.html")
    
@app.route("/history")
@login_required
def history():
    """Show history of transactions."""
    session["stocks"] = []
    stocks = db.execute("SELECT * from stocks WHERE user_id=:user_id", user_id=session["user_id"])
    if stocks:
        session["debug"] = stocks[0]["ticker"]
        session["total"] = 0
        for i in stocks:# [ { }, { }]
            block={}
            stock = lookup(i.get("ticker"))
            block["name"] = stock["name"]
            block["ticker"] = stock["symbol"]
            block["price"] = i["price"]
            block["num_shares"] = i["num_shares"]
            block["method"] = i["method"]
            block["date"] = i["date"]
            session["stocks"].append(block)
        user_balance = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
        user_balance = user_balance[0]["cash"]
        session["balance"] = user_balance
    

    return render_template("history.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    
    # if method is get, 
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method=="POST":
        if not request.form.get("ticker_symbol"):
            return apology("Must provide a ticker symbol")
        quote = lookup(request.form.get("ticker_symbol"))#returns a dictionary
        if not quote:
            return apology("Ticker Symbol Not Found")
        session["quotes"] = quote
        
        return render_template("quoted.html")                   
    else: #The request.method was GET, in which case return a form.
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    # forget any user_id
    session.clear()
    
    if request.method=="POST":
        username = ""
        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password") or not request.form.get("password_confirmation"):
            return apology("must provide password")
        # and that the passwords are matching
        elif not (request.form.get("password")==request.form.get("password_confirmation")):
            return apology("Passwords don't match")
        # prereqs: username is given, password and confirmation are similar.
        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        
        # ensure there are no duplicate usernames
        if len(rows) == 1:
            return apology("Username already taken.")
        # Then username is unique.ghh/onhq
        db.execute("INSERT INTO users (username, hash) values ( :username, :hash)", username=request.form.get("username"), hash=pwd_context.hash(request.form.get("password")))
        rows = db.execute("SELECT id FROM users WHERE username = :username", username=request.form.get("username"))


        # remember which user has logged in
        session["user_id"] = rows[0]

        # redirect user to home page
        return redirect(url_for("index"))
    else: #the request method was get
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    user_balance = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
    user_balance = user_balance[0]["cash"]
    session["balance"] = user_balance
    if request.method=="POST":
        #[ A negative amount of shares?]
        num_shares = request.form.get("shares_num")
        if not request.form.get("ticker_symbol"):
            return apology("Need a ticker symbol")
        if not num_shares:
            return apology("Number of shares not given")
        if not num_shares.isdigit():
            return apology("Input for number of shares must be a number")
        stock = lookup(request.form.get("ticker_symbol"))
        if not stock:
            return apology("Invalid ticker symbol")
        num_shares = int(num_shares)
        if num_shares < 0:
            return apology("Number of shares must be greater than or equal to 0")
        stocks = db.execute("SELECT * from stocks WHERE user_id = :user_id AND ticker=:ticker", user_id = session["user_id"],ticker=stock["symbol"])
        shares = 0
        for i in stocks:
            if i["method"]=="BUY":
                shares+=i["num_shares"]
            else:
                shares-=i["num_shares"]
        if num_shares > shares:
            num_shares = shares
        #EXECUTE SELL!
        db.execute("INSERT INTO stocks (user_id, ticker, num_shares,method,price,date) VALUES(:user_id, :ticker, :num_shares,:method,:price,:date)", user_id=session["user_id"], ticker=stock["symbol"], num_shares=num_shares, method="SELL", price=stock["price"], date=str(datetime.datetime.now()))
        db.execute("UPDATE users SET cash=:cash WHERE id=:user_id", cash=user_balance + (num_shares*stock["price"]), user_id=session["user_id"])
        
    user_balance = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
    user_balance = user_balance[0]["cash"]
    session["balance"] = user_balance
    return render_template("sell.html")
