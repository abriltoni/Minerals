import os
from cs50 import SQL
import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

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


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///minerals.db")

# Connection to be able to create tables from this file
conn = sqlite3.connect('minerals.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# For the "/add" route:
COUNT = 0
NAME = ""


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show a list of all the minerals in de database"""
    """ & Show checkboxes to identify a mineral"""

    # Remove all None values
    #From: https://stackoverflow.com/questions/33797126/proper-way-to-remove-keys-in-dictionary-with-none-values-in-python
    def clean_values(query):
        for value in query:
            clean = {k: v for k, v in value.items() if v is not None}
            value.clear()
            value.update(clean)

    # List of all the column names in users_minerals table
    def headers_list():
        headers = db.execute("SELECT name FROM PRAGMA_TABLE_INFO('users_minerals')")
        for header in headers:
            LIST.append(header['name'])
        del LIST[0:2]
        del LIST[-1]

    # Function to call every time a checkbox is checked
    def make_filter(col_name, attr):
        c.execute("CREATE TEMPORARY TABLE second_temp AS SELECT * FROM first_temp WHERE ({}) = :attr"
                .format(col_name), {"attr" : attr})
        c.execute("DROP TABLE first_temp")
        c.execute("CREATE TEMPORARY TABLE first_temp AS SELECT * FROM second_temp")
        c.execute("DROP TABLE second_temp")
        conn.commit()

    # Reorder the data:
    # Makes a list of dictionaries where keys are the column names
    # And the key values are ordered and without repeated values
    def reorder_data():
        tmp = []
        myDict = {}
        for header in LIST:
            for value in values:
                if header in value:
                    tmp.append(value[header])
            tmp.sort()
            tmp = list(dict.fromkeys(tmp))
            myDict[header] = tmp
            leviathan.append(myDict)
            myDict = {}
            tmp = []

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Headers list
        LIST = []
        headers_list()

        # Query the properties of the selected mineral in the root page
        # In order to display its properties in the /quote page
        if request.form.get("min_name"):

            # Ensure that the clicked mineral is in users_minerals
            names = db.execute("SELECT name FROM users_minerals WHERE user_id=:user",
                            user = session["user_id"])
            n = []
            for name in names:
                n.append(name['name'])
            if request.form.get("min_name") not in n:
                return apology("introduce a correct mineral name", 403)

            values = db.execute("SELECT * FROM users_minerals WHERE user_id=:user AND name=:name",
                                user=session["user_id"], name=request.form.get("min_name"))
            return render_template("quoted.html", values=values)

        # In order to get the appropiate key of the request i.e. request.form.get('color')
        # Where 'color' could be any column name of the table users_minerals
        column_name = []
        attribute = []
        keys = request.form.keys()
        for key in keys:
            column_name.append(key)
            attribute.append(request.form.get(key))
        column_name = column_name[0]
        attribute = attribute[0]

        # Ensure the column name and the mineral name are in the users_minerals
        if column_name not in LIST:
            return apology("Must select a correct property", 403)

        NAMES = []
        count = 0
        names = db.execute("SELECT ({}) FROM users_minerals WHERE user_id = :user_id"
                        .format(column_name), user_id = session['user_id'])
        for name in names:
            NAMES.append(name[column_name])
            if type(name[column_name]) == float:
                count = 1
        if count == 1 and float(attribute) not in NAMES:
            return apology("Must select a correct attribute", 403)
        if count == 0 and attribute not in NAMES:
            return apology("Must select a correct attribute", 403)

        # Call the function to filter the results
        make_filter(column_name, attribute)

        # Query + remove None results
        values = []
        c.execute("SELECT * FROM first_temp")
        for v in c.fetchall():
            values.append(dict(v))
        clean_values(values)

        # Reorder the data:
        # Makes a list of dictionaries where keys are the column names
        # And the key values are ordered and without repeated values
        leviathan = []
        reorder_data()

        # Query the names of the selection
        names = []
        c.execute("SELECT name FROM first_temp")
        for n in c.fetchall():
            names.append(n['name'])
        names.sort()
        return render_template("index.html", values = leviathan, names = names, LIST = LIST)


    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Headers list
        LIST = []
        headers_list()

        # Query data of all minerals in users_minerals and clean None values
        values = db.execute("SELECT * FROM users_minerals WHERE user_id=:user",
                            user = session["user_id"])
        clean_values(values)

        # Reorder the data:
        # Makes a list of dictionaries where keys are the column names
        # And the key values are ordered and without repeated values
        leviathan = []
        reorder_data()

        # Ordered list of all the names in the table
        names = []
        NAMES = db.execute("SELECT name FROM users_minerals WHERE user_id=:user",
                        user = session["user_id"])
        for name in NAMES:
            names.append(name['name'])
        names.sort()

        # Ensure there is no table with first_temp or second_temp name
        c.execute("DROP TABLE IF EXISTS first_temp")
        c.execute("DROP TABLE IF EXISTS second_temp")

        # Create first_temp with all the contents of users_minerals table
        c.execute("CREATE TEMPORARY TABLE first_temp AS SELECT * FROM users_minerals WHERE user_id = :user",
                {'user' : session['user_id']})
        conn.commit()

        return render_template("index.html", values = leviathan, LIST = LIST, names=names)


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add new minerals to users_minerals"""

    # In order to use global variables inside this app.route
    global COUNT
    global NAME

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure correct field names
        HEADERS = []
        headers = db.execute("SELECT name FROM PRAGMA_TABLE_INFO('users_minerals')")
        for header in headers:
            HEADERS.append(header['name'])
        del HEADERS[0:2]

        # Get access to the pair of values when a form is submited
        k = []
        v = []
        keys = request.form.keys()
        for key in keys:
            values = request.form.get(key)
            if values == "":
                values = None
            if key not in HEADERS:
                if COUNT >=1:
                    db.execute("DELETE FROM users_minerals WHERE user_id=:user AND name=:name",
                            user=session['user_id'], name = NAME)
                return apology("You must not modify field names", 403)
            k.append(key)
            v.append(values)

            # Transform input into lower case and capitalized
            v = [n.lower().capitalize() if n != None else None for n in v]

        # Insert the name of a new mineral into users_minerals. All the other properties will be set as NULL
        if COUNT == 0:
            # Chack if the name currently exists on the users_minerals table
            names = db.execute("SELECT name FROM users_minerals WHERE user_id = :user", user = session['user_id'])
            for name in names:
                if v[0] in name['name']:
                    return apology("name currently in your data base", 403)
            db.execute("INSERT INTO users_minerals (user_id, name) VALUES (?, ?)",
                   session['user_id'], v[0])
            NAME = v[0]
            COUNT+=1
            return render_template("add_optical.html", name=NAME)

        # Modify optical properties of that new mineral
        if COUNT == 1:
            db.execute("UPDATE users_minerals SET streak = :streak, color = :color, patina = :patina, patina_color = :patina_color, luster = :luster, crystal_system = :crystal_system, crystal_shape = :crystal_shape, face_surface = :face_surface, external_aspect = :external_aspect, diaphanety = :diaphanety WHERE user_id = :user_id AND name = :name",
                    user_id = session['user_id'], name = NAME, streak = v[0], color = v[1], patina = v[2], patina_color = v[3], luster = v[4], crystal_system = v[5], crystal_shape = v[6], face_surface = v[7], external_aspect = v[8], diaphanety = v[9])
            COUNT+=1
            return render_template("add_mechanical.html", name=NAME)

        # Modify mechanical properties of that new mineral
        if COUNT == 2:
            db.execute("UPDATE users_minerals SET mohs_hardness = :mohs_hardness, specific_gravity = :specific_gravity, exfoliation = :exfoliation, cleavage = :cleavage, tenacity = :tenacity WHERE user_id = :user_id AND name = :name",
                    user_id = session['user_id'], name = NAME, mohs_hardness = v[0], specific_gravity = v[1], exfoliation = v[2], cleavage = v[3], tenacity = v[4])
            COUNT+=1
            return render_template("add_other.html", name=NAME)

        # Modify other properties of that new mineral
        if COUNT == 3:
            db.execute("UPDATE users_minerals SET induced_magnetism = :induced_magnetism, radioactivity_cps = :radioactivity_cps, touch = :touch, taste = :taste, smell = :smell, effervescence = :effervescence WHERE user_id = :user_id AND name = :name",
                    user_id = session['user_id'], name = NAME, induced_magnetism = v[0], radioactivity_cps = v[1], touch = v[2], taste = v[3], smell = v[4], effervescence = v[5])
            COUNT = 0
            NAME = ""
            return redirect("/")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        COUNT = 0
        NAME = ""
        return render_template("add.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("You must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("You must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

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
@login_required
def quote():
    """Get mineral quote"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure that a mineral has been introduced and its correct
        names = db.execute("SELECT name FROM users_minerals WHERE user_id=:user",
                        user = session["user_id"])
        n = []
        for name in names:
            n.append(name['name'])
        if not request.form.get("min_name") or request.form.get("min_name") not in n:
            return apology("introduce a correct mineral name", 403)

        values = db.execute("SELECT * FROM users_minerals WHERE user_id=:user AND name=:name",
                            user=session["user_id"], name=request.form.get("min_name"))

        return render_template("quoted.html", values=values)


    # User reached route via GET (as by clicking a link or via redirect)
    else:
        names = []
        minerals = db.execute("SELECT name FROM users_minerals WHERE user_id=:user",
                           user=session["user_id"])
        for mineral in minerals:
            names.append(mineral["name"])
        names.sort()
        return render_template("quote.html", names=names)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("You must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("You must provide password", 403)

        # Ensure  confirm password was submitted
        elif not request.form.get("confirm_password"):
            return apology("You must provide confirmation password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username do not exists
        if len(rows) != 0:
            return apology("username not available", 403)

        # Ensure password and confirmation password are equals
        if request.form.get("password") != request.form.get("confirm_password"):
            return apology("passwords aren't equal", 403)

        # Store username into the database
        # Hash the users password and store that hash into the database
        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password")) #generate_password_hash

        db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", username=username, password=password)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Fill users_minerals table with default minerals
        values = db.execute("SELECT * FROM base")
        for value in values:
            db.execute("INSERT INTO users_minerals (user_id, streak, color, patina, patina_color, luster, crystal_system, crystal_shape, face_surface, external_aspect, diaphanety, mohs_hardness, specific_gravity, exfoliation, cleavage, tenacity, induced_magnetism, radioactivity_cps, touch, taste, smell, effervescence, name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        session["user_id"], value["streak"], value["color"], value["patina"], value["patina_color"], value["luster"], value["crystal_system"], value["crystal_shape"], value["face_surface"], value["external_aspect"], value["diaphanety"], value["mohs_hardness"], value["specific_gravity"], value["exfoliation"], value["cleavage"], value["tenacity"], value["induced_magnetism"], value["radioactivity_cps"], value["touch"], value["taste"], value["smell"], value["effervescence"], value["name"])

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/modify", methods=["GET", "POST"])
@login_required
def modify():
    """Modify mineral properties"""

    NAMES = []
    HEADERS = []
    def names_and_headers():
        # List of all mineral names
        names = db.execute("SELECT name FROM users_minerals WHERE user_id = :user_id",
                        user_id = session['user_id'])
        for name in names:
            NAMES.append(name['name'])
        NAMES.sort()

        # List of all the column names in users_minerals table
        headers = db.execute("SELECT name FROM PRAGMA_TABLE_INFO('users_minerals')")
        for header in headers:
            HEADERS.append(header['name'])
        del HEADERS[0:2]


    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure name and property in users_minerals
        names_and_headers()
        if request.form.get("name") not in NAMES or request.form.get("properties") not in HEADERS:
            return apology("Must select a correct name and a correct property", 403)

        # Get access to the pair of values when a form is submited
        k = []
        v = []
        keys = request.form.keys()
        for key in keys:
            values = request.form.get(key)
            if values == "":
                values = None
            k.append(key)
            v.append(values)

            # Transform values into lower case and capitalized
            v = [n.lower().capitalize() if n != None else None for n in v]

        db.execute("UPDATE users_minerals SET ({}) = :value WHERE user_id = :user_id AND name = :name"
                .format(v[1].lower()), user_id = session['user_id'], name = v[0], value = v[2])

        # Display the values with the last modification
        NAMES = []
        HEADERS = []
        names_and_headers()

        return render_template("modify.html", names=NAMES, properties=HEADERS)

    else:
        names_and_headers()

        return render_template("modify.html", names=NAMES, properties=HEADERS)


@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    """Delete minerals from users_minerals"""

    if request.method == "POST":

        # Ensure the name exists in the users_minerals
        names = db.execute("SELECT name FROM users_minerals WHERE user_id=:user_id",
                        user_id = session['user_id'])
        n = []
        for name in names:
            n.append(name['name'])
        if request.form.get("name") not in n:
            return apology("Must introduce a correct name", 403)

        # Delete the mineral
        name = request.form.get("name")
        db.execute("DELETE FROM users_minerals WHERE user_id = :user_id AND name = :name",
                user_id = session['user_id'], name = name)

        # Reload the list of names without the deleted one
        NAMES = []
        names = db.execute("SELECT name FROM users_minerals WHERE user_id = :user_id",
                        user_id = session['user_id'])
        for name in names:
            NAMES.append(name['name'])
        NAMES.sort()
        return render_template("delete.html", names = NAMES)

    else:
        NAMES = []
        names = db.execute("SELECT name FROM users_minerals WHERE user_id = :user_id",
                        user_id = session['user_id'])
        for name in names:
            NAMES.append(name['name'])
        NAMES.sort()
        return render_template("delete.html", names = NAMES)


def errorhandler(e):
    """Handle error"""

    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
