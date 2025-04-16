from flask import Flask, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector

app = Flask(__name__)

conn = mysql.connector.connect(
    host="localhost", user="root", password="admin", database="finance"
)

cursor = conn.cursor()


# Serve the main transaction logging page
@app.route("/index.html")
def index_page():
    return render_template("index.html")


# Serve the main transaction logging page
@app.route("/")
def index():
    # return render_template("login_register.html")
    return render_template("index.html")


# Serve the category addition page
@app.route("/add_category.html")
def add_category_page():
    return render_template("add_category.html")


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    password_hash = generate_password_hash(password)
    cursor.execute(
        "INSERT INTO USERS(Name,Email,Password_Hash) VALUES('{}','{}','{}')".format(
            username, email, password_hash
        )
    )
    conn.commit()
    print(cursor.rowcount)
    return jsonify({"message": "Success"}), 200


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    cursor.execute(
        "SELECT User_ID, Password_Hash from USERS WHERE Name = '{}'".format(username)
    )
    user = cursor.fetchone()
    print(user[1])
    # Check if user exists
    if user and check_password_hash(user[1], password):
        # return jsonify({"message": "Login successful", "user": user[0]}), 200
        return index_page()
    else:
        return jsonify({"error": "Invalid credentials"}), 401


@app.route("/dashboard/<uid>", methods=["GET"])
def get_transactions(uid):
    cursor.execute(
        "SELECT DATE_FORMAT(Month_Year,'%d-%m-%Y') AS FormattedDate,Category,Description,Amount FROM Transactions WHERE User_ID = {} ORDER BY Month_Year DESC".format(
            uid
        )
    )
    columns = ["Month_Year", "Category", "Description", "Amount"]
    data = cursor.fetchall()
    transactions = [dict(zip(columns, row)) for row in data]
    results = get_monthly_limits(uid)
    if data:
        return (
            jsonify({"monthly_limits": results, "transactions": transactions}),
            200,
        )
    elif not data and results:
        return jsonify({"monthly_limits": results, "transactions": []})
    else:
        return jsonify({"message": "Nothing to Return!"}), 200


"""PLEASE DELETE THIS FUNCTION BEFORE PUSHING TO PROD"""


@app.route("/fetch", methods=["GET"])
def get_all():
    cursor.execute("SELECT * FROM USERS")
    data = cursor.fetchall()
    return jsonify(data), 200


def update_balance(user_id, category, amount):
    cursor.execute(
        "SELECT Remaining_Monthly_Limit FROM Budgets WHERE User_ID = {} AND Category = '{}'".format(
            user_id, category
        )
    )
    data = cursor.fetchone()
    print(data, amount)
    updated_balance = int(data[0]) - int(amount)
    cursor.execute(
        "UPDATE Budgets SET Remaining_Monthly_Limit = {} WHERE User_ID = {} AND Category = '{}'".format(
            updated_balance, user_id, category
        )
    )

    conn.commit()

    return cursor.rowcount


@app.route("/addtxn", methods=["POST"])
def add_record():
    data = request.get_json()
    user_id = data.get("userID")
    date = data.get("date")
    description = data.get("description")
    category = data.get("category")
    amount = data.get("amount")

    cursor.execute(
        "INSERT INTO Transactions(User_ID,Category,Amount,Month_Year,Description) VALUES('{}','{}','{}','{}','{}')".format(
            user_id, category, amount, date, description
        )
    )

    conn.commit()

    status = update_balance(user_id, category, amount)

    if cursor.rowcount == 1 and status == 1:
        return jsonify({"message": "success"}), 200
    else:
        return jsonify({"error": "Invalid Data"}), 401


@app.route("/addcategory", methods=["POST"])
def add_category():
    data = request.get_json()
    user_id = data.get("userID")
    category = data.get("category")
    monthly_limit = data.get("monthlyLimit")
    curr_balance = monthly_limit

    cursor.execute(
        "INSERT INTO Budgets (User_ID,Category,Monthly_Limit,Remaining_Monthly_Limit) VALUES('{}','{}','{}','{}')".format(
            user_id, category, monthly_limit, curr_balance
        )
    )

    conn.commit()

    if cursor.rowcount == 1:
        return jsonify({"message": "success"}), 200
    else:
        return jsonify({"error": "Invalid Data"}), 401


def get_monthly_limits(user_id):

    cursor.execute(
        "SELECT Category, Monthly_Limit, Remaining_Monthly_Limit FROM Budgets WHERE User_ID = {}".format(
            user_id
        )
    )

    data = cursor.fetchall()

    results = []
    for cat, total_limit, budget in data:
        results.append(
            {
                "category": cat,
                "budget": float(budget),
                "total_budget": float(total_limit),
            }
        )

    print(results)
    return results


if __name__ == "__main__":
    app.run(debug=True)
