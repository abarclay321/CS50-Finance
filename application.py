import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # Determine 1) which stocks and 2) quantity owned by current user
    stocks = []
    stocks = db.execute("SELECT symbol, SUM(quantity) FROM simple WHERE userID = :user GROUP BY symbol", user = session["user_id"])

# Add current price and company name to dict stocks
    # Add name to stocks dictionary
    for i in range(len(stocks)):
        # lookup a quote of stock using it's symbol
        quote=lookup(stocks[i]["symbol"])
        # add the name of each stock to stocks dictionary
        stocks[i]["name"] = quote["name"]
    # Add current price to dictionary
    for i in range(len(stocks)):
        # lookup a quote of stock using it's symbol
        quote=lookup(stocks[i]["symbol"])
        # add the price of each stock to stocks dictionary
        stocks[i]["price"] = quote["price"]

# Equity
    # Calc equity value of stocks owned by current user
    totEquity = 0
    for i in range(len(stocks)):
        # determine total equity value for each stock owned by current user
        stocks[i]["equity"] = stocks[i]["price"] * stocks[i]["SUM(quantity)"]
        totEquity += stocks[i]["equity"]

# Cash
    # Pull current cash from table
    currCash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
    # Process into int value
    currCash = currCash[0]["cash"]

    return render_template("index.html", stocks = stocks, currCash = usd(currCash), total = usd(currCash + totEquity))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # lookup a quote of the given symbol
        q = lookup(request.form.get("symbol"))
        # ensure searched symbol exists
        if q == None:
            return apology("Symbol doesn't exist", 400)

        # shares user wants to buy
        toBuy = int(request.form.get("shares"))
        # ensure positive number
        if toBuy < 1:
            return apology("Must input positive number", 400)

        #determine costs of purchase
        purchPrice = q["price"] * toBuy
        # print(purchPrice)

        # ensure purchase price is less than remaining cash
        # Pull current cash from table
        currCash = db.execute("SELECT cash FROM users WHERE id = :id", id = session["user_id"])
        # Process into int value
        currCash = currCash[0]["cash"]
        # Compare current cash to amount needed for purchase
        if currCash < purchPrice:
            return apology("You can't afford this purchase without depositing additional funds", 400)

    # buy stock by 1) subtracting cash 2) adding stock to portfolio
        # subtracting cash
        db.execute("UPDATE users SET cash = cash - :spent Where id = :id", spent = purchPrice, id = session["user_id"])

        # documenting stock purchases so they can be summarized in a portfolio later
        db.execute("INSERT INTO simple (symbol, quantity, price, userID) VALUES (:symbol, :quantity, :price, :userID)",
                                        symbol = q["symbol"], quantity = toBuy, price = q["price"], userID = session["user_id"])

        # test=db.execute("SELECT * FROM simple")
        # print(test)

        return redirect("/")
    # get requests
    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    # Get Username entered
    username = request.args.get('username')

    # Query database for username
    rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

    # If username exists/is taken, return false
    if len(rows) > 0:
        return jsonify(False) #taken
    else:
        return jsonify(True) #not


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # Determine 1) which stocks and 2) quantity owned by current user
    trans = []
    trans = db.execute("SELECT * FROM simple WHERE userID = :user", user = session["user_id"])
    numtrans = range(len(trans))
# Add current price and company name to dict stocks
    # Add name to stocks dictionary
    for i in range(len(trans)):
        # lookup a quote of stock using it's symbol
        quote=lookup(trans[i]["symbol"])
        # add the name of each stock to stocks dictionary
        trans[i]["name"] = quote["name"]
    # Add current price to dictionary
    for i in range(len(trans)):
        # lookup a quote of stock using it's symbol
        quote=lookup(trans[i]["symbol"])
        # add the price of each stock to stocks dictionary
        trans[i]["price"] = quote["price"]
    return render_template("history.html", trans = trans, numtrans = numtrans)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
# @login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        # lookup a quote of the given symbol
        q=lookup(request.form.get("symbol"))
        # ensure searched symbol exists
        if q == None:
            return apology("Symbol doesn't exist", 400)
        # print(q)
        # name=quote["name"]
        # price=quote["price"]
        # symbol=quote["price"]
        return render_template("quoted.html", quote=q)
    else:
        return render_template("quote.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

# User clicks register to submit their login
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

# Validate all information (4) was submitted & hash pwd
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)

        # Ensure confirmation matches password
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords must match", 400)

        # Hash Password
        pwhash = generate_password_hash(request.form.get("password"))

# Register user by storing username and hashed pw in DB
        db.execute("INSERT INTO users (username, hash) VALUES (:username,:hash)",
                    username=request.form.get("username"), hash=pwhash)


# Automatically log in user - Future feature
#       session["user_id"] = rows[0]["id"]

        # Redirect user to login page
        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        # lookup a quote of the given symbol
        q = lookup(request.form.get("symbol"))
        # ensure searched symbol exists
        if q == None:
            return apology("Symbol doesn't exist", 400)

# ensure user has enough shairs to sell
        # determine amount of that stock the current user owns
        shares = db.execute("SELECT SUM(quantity) FROM simple WHERE userID = :user AND symbol = :symbol", user = session["user_id"], symbol = request.form.get("symbol"))
        # print(shares)
        # process into int
        shares = shares[0]["SUM(quantity)"]

        # number of shares user wants to sell
        toSell = int(request.form.get("shares"))
        # ensure positive number
        if toSell < 1:
            return apology("Must input positive number", 400)

        # compare shares to be sold vs shares owned
        if toSell > shares :
            return apology("Cannot sell more than you own", 400)

        #determine earnings from sale
        salePrice = q["price"] * toSell

    # sell stock by 1) subtracting cash 2) adding stock to portfolio
        # subtracting cash
        db.execute("UPDATE users SET cash = cash + :gained WHERE id = :id", gained = salePrice, id = session["user_id"])

        # documenting stock purchases so they can be summarized in a portfolio later
        db.execute("INSERT INTO simple (symbol, quantity, price, userID) VALUES (:symbol, :quantity, :price, :userID)",
                                        symbol = q["symbol"], quantity = -toSell, price = q["price"], userID = session["user_id"])

        return redirect("/")
    # get requests
    else:
        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
