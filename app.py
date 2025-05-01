from flask import Flask, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from flask import session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import pandas as pd
load_dotenv()
app = Flask(__name__)
app.secret_key = 'unaku_vaikuren_da_periya_aapa'

conn = mysql.connector.connect(
    host=os.getenv('HOST'), user=os.getenv("USER"), password=os.getenv("PASSWORD"), database=os.getenv("DATABASE")
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
    return render_template("login_register.html")


# Serve the category addition page
@app.route("/add_category.html")
def add_category_page():
    return render_template("add_category.html")


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    hashed_password = generate_password_hash(password)

    try:
        cursor.execute(
            "INSERT INTO USERS(Name, Email, Password_Hash) VALUES (%s, %s, %s)",
            (username, email, hashed_password)
        )
        conn.commit()

        # Fetch the new user's ID
        cursor.execute("SELECT User_ID FROM USERS WHERE Email = %s", (email,))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]  # Log the user in by setting session
            return jsonify({"message": "Registration successful", "userID": user[0]}), 200
        else:
            return jsonify({"error": "Could not retrieve user ID"}), 500

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500



@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    cursor.execute(
        "SELECT User_ID, Password_Hash from USERS WHERE Name = '{}'".format(username)
    )
    user = cursor.fetchone()

    # Check if user exists and password matches
    if user and check_password_hash(user[1], password):
        # Store the user_id in the session
        session['user_id'] = user[0]
        
        return jsonify({"message": "Login successful", "userID": user[0]}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401


@app.route("/dashboard", methods=["GET"])
def get_transactions():
    uid = session.get("user_id") 
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

def update_remaining(category,amount):
    user_id = session.get("user_id")
    cursor.execute(
        "SELECT SUM(Amount) AS TotalAmount FROM transactions WHERE User_ID = {} AND Category = '{}'".format(user_id,category) 
    )
    result = cursor.fetchone()
    total_amount = result[0] if result[0] is not None else 0.0

    updated_balance = int(amount-total_amount)
    cursor.execute(
        "UPDATE Budgets SET Remaining_Monthly_Limit = {} WHERE User_ID = {} AND Category = '{}'".format(
            updated_balance, user_id, category
        )
    )

    conn.commit()
    return cursor.rowcount
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
    user_id = session.get("user_id") 
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

    user_id = session.get("user_id")  # or use data.get("userID") if session isn't available
    if not user_id:
        return jsonify({"error": "User not logged in or userID missing"}), 401

    category = data.get("category")
    monthly_limit = data.get("monthlyLimit")
    curr_balance = monthly_limit
    print("hii")
    cursor.execute(
        "INSERT INTO Budgets (User_ID, Category, Monthly_Limit, Remaining_Monthly_Limit) VALUES (%s, %s, %s, %s)",
        (user_id, category, monthly_limit, curr_balance)
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
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    if not file.filename.endswith(('.xls', '.xlsx')):
        return "Invalid file format", 400

    # Read Excel file
    df = pd.read_excel(file)

    user_id = session.get('user_id')
    if not user_id:
        return "User not logged in", 401

    for index, row in df.iterrows():
        category = row['Category']
        amount = float(row['Amount'])
        date = str(row['Month_Year'])
        description = row['Description']

        # Check if budget exists for this (user, category)
        cursor.execute("SELECT 1 FROM Budgets WHERE User_ID = %s AND Category = %s", (user_id, category))
        if not cursor.fetchone():
            # Create new budget with default ₹10,000
            cursor.execute(
                "INSERT INTO Budgets (User_ID, Category, Monthly_Limit, Remaining_Monthly_Limit) VALUES (%s, %s, %s, %s)",
                (user_id, category,0,0)
            )
            conn.commit()

        # Insert transaction
        cursor.execute(
            "INSERT INTO Transactions (User_ID, Category, Amount, Month_Year, Description) VALUES (%s, %s, %s, %s, %s)",
            (user_id, category, amount, date, description)
        )
        conn.commit()

        # Optionally update balance if needed
        update_balance(user_id, category, amount)

    return jsonify({"message": "Excel data uploaded and processed successfully!"}), 200

@app.route('/editbudget', methods=['PUT'])
def edit_budget():
    user_id = session.get('user_id')  # if you're using sessions
    print(user_id)
    if not user_id:
        return "User not logged in", 401
    data = request.get_json()
    category = data['category']
    new_budget = data['updatedBudget']
    print(new_budget)
    print(category)
    # Update logic
    cursor.execute("UPDATE budgets SET Monthly_Limit = {}, Remaining_Monthly_Limit = {} WHERE User_ID = {} AND Category = '{}'".format(new_budget,0 , user_id, category))
    conn.commit()
    status = update_remaining(category, new_budget)

    if cursor.rowcount == 1 and status == 1:
        return jsonify({"message": "success"}), 200
    else:
        return jsonify({"error": "Invalid Data"}), 401
    # return jsonify({"message": "Budget updated"}), 200

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
