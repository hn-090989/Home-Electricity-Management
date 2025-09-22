import os

from flask import Flask, redirect, render_template, session, request, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from datetime import datetime, timedelta

from helpers import login_required

app = Flask(__name__)


app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/", methods=["POST", "GET"])
@login_required
def dashboard():
    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()

    # total power consumed
    cursor.execute("SELECT SUM(power_consumed / 1000.0 * (5.0/60.0)) AS power FROM power_logs WHERE user_id=? AND strftime('%Y-%m-%d', time) = strftime('%Y-%m-%d', 'now')", (session["user_id"],))
    row = cursor.fetchone()
    today = row[0] if row and row[0] is not None else 0

    cursor.execute("SELECT SUM(power_consumed / 1000.0 * (5.0/60.0)) AS power FROM power_logs WHERE user_id=? AND date(time) BETWEEN date('now', '-6 days') AND date('now')", (session["user_id"],))
    row = cursor.fetchone()
    this_week = row[0] if row and row[0] is not None else 0

    cursor.execute("SELECT SUM(power_consumed / 1000.0 * (5.0/60.0)) AS power FROM power_logs WHERE user_id=? AND strftime('%Y-%m', time) = strftime('%Y-%m', 'now')", (session["user_id"],))
    row = cursor.fetchone()
    this_month = row[0] if row and row[0] is not None else 0

    # the bill so far this month
    if this_month <= 100:
        bill = this_month* 7
    elif this_month <= 200:
        bill = this_month * 10
    else :
        bill = this_month * 15

    # bill at the same month last year and number of units consumed during the same month last year
    cursor.execute("""
                SELECT power_consumed,  bill_amount FROM bills
                WHERE user_id=? AND strftime('%Y-%m', billed_at) = strftime('%Y-%m', 'now', '-1 year')
             """,(session["user_id"],))
    rows = cursor.fetchall()
    last_month = [{"units": row[0], "bill": row[1]} for row in rows]

    cursor.execute("SELECT name FROM users WHERE id=?", (session["user_id"],))
    row = cursor.fetchone()
    if row:
        name = row[0]
    else:
        name= "User"

    conn.close()
    return render_template("dashboard.html", today= today, this_week= this_week, this_month= this_month, bill=bill, last_month= last_month, name=name)


@app.route("/get_data", methods=["GET"])
@login_required
def graph_data():
    type = request.args.get("log_type")
    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()

    if type == "hourly":
        cursor.execute(""" SELECT strftime('%H', time) || ':' || printf('%02d', (CAST(strftime('%M', time) AS INTEGER))) AS minute,
                SUM(power_consumed / 1000.0 * (5.0/60.0)) AS power
                FROM power_logs
                WHERE date(time) = date('now') AND user_id=?
                GROUP BY strftime('%Y-%m-%d %H', time), (CAST(strftime('%M', time) AS INTEGER))
                ORDER BY minute""", (session["user_id"],))

    elif type == "daily":
        cursor.execute("""SELECT strftime('%m-%d   %H:00', time) AS hour, SUM(power_consumed / 1000.0 * (5.0/60.0)) AS power
                FROM power_logs
                WHERE user_id=? AND date(time) BETWEEN date('now', '-6 days') AND date('now')
                GROUP BY hour
                ORDER BY hour""", (session["user_id"],))

    elif type == "monthly":
        cursor.execute("""SELECT strftime('%d', time) AS day, SUM(power_consumed / 1000.0 * (5.0/60.0)) AS power
                FROM power_logs
                WHERE strftime('%Y-%m', time) = strftime('%Y-%m', 'now') AND user_id=?
                GROUP BY day
                ORDER BY day""", (session["user_id"],))

    rows = cursor.fetchall()
    data = [{"time":row[0], "power": row[1]} for row in rows]

    conn.close()

    return jsonify({"data": data})


@app.route("/login", methods=["POST", "GET"])
def login():
    session.clear()
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
             return render_template("login.html", error="Please provide a username")

        elif not password:
             return render_template("login.html", error="Invalid username or password")

        conn = sqlite3.connect("management.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, hash FROM users WHERE user_name = ?",(username,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return render_template("login.html", error="Invalid username or password")
        if not check_password_hash(row[1], password):
             return render_template("login.html", error="Invalid username or password")

        session.permanent = True
        session["user_id"] = row[0]
        return redirect ("/")
    else:
        return render_template("login.html")


 # code for appliance page
@app.route("/appliances", methods=['POST', 'GET'])
@login_required
def appliances():

    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()
    # data for pie chart
    cursor.execute("""SELECT appliances.id AS ID, appliances.name AS name, appliances.power_rating AS wattage, SUM(power_logs.power_consumed / 1000.0 * (5.0/60.0)) AS total_power
                   FROM power_logs
                   JOIN appliances
                   ON appliances.id = power_logs.appliance_id
                   WHERE strftime('%Y-%m', time) = strftime('%Y-%m', 'now') AND appliances.user_id=?
                   GROUP BY appliances.id
                   ORDER BY total_power DESC""", (session["user_id"],))
    rows = cursor.fetchall()
    cursor.close()
    monthly_sum = [
        {"id": row[0], "name": row[1], "wattage": row[2], "total_power": row[3]}
        for row in rows
    ]
    top_appliances = monthly_sum[:3]

    cursor = conn.cursor()
    cursor.execute("SELECT id, name, power_rating FROM appliances WHERE user_id=?", (session["user_id"],))
    rows = cursor.fetchall()
    appliances = [
        {"id": row[0], "name": row[1], "wattage": row[2]}
        for row in rows
    ]
    conn.close()
    return render_template("appliances.html", monthly_sum=monthly_sum, top_appliances=top_appliances, appliances=appliances)


# API routes
# getting an appliances data for a detailed line graph
@app.route("/get_appliance_data", methods=['GET'])
@login_required
def appliance_data():
    applianceID = request.args.get("appliance")
    timeStamp = request.args.get("type", "monthly")

    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()

    if timeStamp == 'monthly':    # this month grouped by day
        cursor.execute("""SELECT strftime('%d', time) AS day, SUM(power_logs.power_consumed / 1000.0 * (5.0/60.0))
                       FROM power_logs
                       JOIN appliances
                       ON appliances.id = power_logs.appliance_id
                       WHERE strftime('%Y-%m', time) = strftime('%Y-%m', 'now') AND appliances.user_id=? AND appliances.id=?
                       GROUP BY day
                       ORDER BY day""", (session["user_id"], applianceID,))

    elif timeStamp == 'daily':   # this day grouped by hour
        cursor.execute("""SELECT strftime('%H-%M', time) AS hour, SUM(power_logs.power_consumed / 1000.0 * (5.0/60.0))
                       FROM power_logs
                       JOIN appliances
                       ON appliances.id = power_logs.appliance_id
                       WHERE strftime('%Y-%m-%d', time) = strftime('%Y-%m-%d', 'now') AND appliances.user_id=? AND appliances.id=?
                       GROUP BY hour
                       ORDER BY hour""", (session["user_id"],applianceID,))

    elif timeStamp == "yearly":  # this year grouped by month
        cursor.execute("""SELECT strftime('%m', time) AS month, SUM(power_logs.power_consumed / 1000.0 * (5.0/60.0))
                       FROM power_logs
                       JOIN appliances
                       ON appliances.id = power_logs.appliance_id
                       WHERE strftime('%Y', time) = strftime('%Y', 'now') AND appliances.user_id=? AND appliances.id=?
                       GROUP BY month
                       ORDER BY month""", (session["user_id"],applianceID,))

    rows = cursor.fetchall()
    data = [{"label": row[0], "logs": row[1]} for row in rows] if rows else []

    conn.close()
    return jsonify({"success": True, "data": data})


@app.route("/add_appliance", methods=['POST'])  # adding an appliance
@login_required
def add_appliance():
    data = request.get_json()

    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()
    if data["applianceWattage"]:
        cursor.execute("INSERT INTO appliances (user_id, name, power_rating) VALUES (?, ?, ?)",
                       (session["user_id"], data["applianceName"], data["applianceWattage"],))
    else:
        cursor.execute("INSERT INTO appliances (user_id, name) VALUES (?, ?)", (session["user_id"], data["applianceName"],))
    conn.commit()
    applianceID = cursor.lastrowid

    conn.close()
    return jsonify ({"success": True, "applianceID": applianceID})


@app.route("/update_appliance", methods=['POST'])  # updating an appliance
@login_required
def update_appliance():
    data = request.get_json()

    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE appliances SET name=?, power_rating=? WHERE id=?",(data["applianceName"], data["applianceWattage"], data["applianceID"],))
    conn.commit()
    conn.close()

    return jsonify ({"success": True})


@app.route("/delete_appliance", methods=['POST'])  # delete an existing applaince
@login_required
def delete_appliance():
    data = request.get_json()

    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appliances WHERE id = ?", (data["applianceID"],))
    conn.commit()
    conn.close()

    return jsonify ({"success": True})


# code for billing page
@app.route("/billing")
@login_required
def billing():
    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()

    bill_generation_check(session["user_id"])

    cursor.execute("""
        SELECT id, month, power_consumed, bill_amount, date_billed, paid
        FROM bills
        WHERE user_id = ?
        AND strftime('%Y', date_billed) = strftime('%Y', 'now')
    """, (session["user_id"],))
    rows = cursor.fetchall()
    if rows:
        bills = [{"id": row[0], "month": row[1], "power_consumed": row[2], "bill_amount": row[3], "date_billed": row[4], "paid": row[5]} for row in rows]
    else:
        bills = []
    conn.close()
    return render_template("billing.html", bills=bills)


def bill_generation_check(user):
    # gets the last month
    today = datetime.now()
    first_day = today.replace(day=1)
    last_month = (first_day - timedelta(days=1)).strftime("%Y-%m")

    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()
    cursor.execute("SELECT month FROM bills WHERE user_id=?", (user,))
    row = cursor.fetchone()

    if not row or row[0] != last_month:
        generate_user_bill(last_month, user);

    conn.close()


def generate_user_bill(last_month, user):
    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()

    cursor.execute("""SELECT SUM(power_consumed/1000.0*(5/60.0))
                FROM power_logs
                WHERE user_id=?
                AND strftime('%Y-%m', time)=?""",(user, last_month,))
    row = cursor.fetchone()
    power_consumed = row[0] if row and row[0] else 0

    if power_consumed <= 100:
        bill = power_consumed * 7
    elif power_consumed <= 200:
        bill = power_consumed * 10
    else:
        bill = power_consumed * 15

    cursor.execute("""INSERT INTO bills (user_id, month, power_consumed, bill_amount, paid)
                   VALUES(?, ?, ?, ?, ?)""", (user, last_month, power_consumed, bill, False, ))
    conn.commit()
    conn.close()


@app.route("/mark_paid", methods=["POST"])
@login_required
def mark():
    conn = sqlite3.connect("management.db")
    cursor = conn.cursor()

    data = request.get_json()
    cursor.execute("UPDATE bills SET paid=? WHERE id=?", (True, data["billID"],))

    conn.commit()
    conn.close()
    return jsonify ({"success": True})

@app.route("/register", methods= ["POST", "GET"])
def register():
     if request.method == 'POST':
        conn = sqlite3.connect("management.db")
        cursor = conn.cursor()

        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        name = request.form.get("name")

        if not username:
             return render_template("register.html", error="Please provide a username")

        if not password:
             return render_template("register.html", error="Please provide a password")

        if not request.form.get("confirmation"):
             return render_template("register.html", error="Please enter the confirmation")

        if not email:
             return render_template("register.html", error="Please provide your email")

        if not name:
             return render_template("register.html", error="Please enter your name")

        cursor.execute("SELECT * FROM users WHERE user_name=?", (request.form.get("username"),))
        rows = cursor.fetchall()

        if len(rows) != 0:
             return render_template("register.html", error="Username already taken")

        if request.form.get("password") != request.form.get("confirmation"):
             return render_template("register.html", error="Please provide a username")

        cursor.execute("INSERT INTO users (user_name, hash, email, name) VALUES(?, ?, ?, ?)", (username, generate_password_hash(password), email, name,))
        conn.commit()

        cursor.execute("SELECT id FROM users WHERE user_name=?", (username,))
        row = cursor.fetchone()
        session["user_id"] = row[0] if row else 0

        conn.close()
        return redirect("/")
     else:
        return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
