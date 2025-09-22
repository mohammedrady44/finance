from flask import Flask, redirect, render_template, request, session,url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import mysql.connector
import func 
from decimal import Decimal

app = Flask(__name__)
ins = mysql.connector.connect(user= "root",password = "7500763",host="127.0.0.1",database = "finance")
cursor = ins.cursor()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/register",methods = ["GET","POST"])
def register():

    if request.method == "POST":
        error = ""
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmation")
        if not username:
            error = "Please enter valid user name"

        elif not password:
            error = "Please enter valid password"

        elif password != confirm_password:
            error = "two passwords aren't the same"

        if error:
            return render_template("register.html",value = error)

        cursor.execute("select * from users where username = %s",(username,))
        results = cursor.fetchall()
        if results:
            return render_template("register.html",value = "user name already taken by another one")
        
        cursor.execute("insert into users(username,hash)values(%s,%s)",(username,generate_password_hash(password)))
        ins.commit()
        cursor.execute("select * from users where username = %s",(username,))
        results = cursor.fetchall()
        session["id"] = results[0][0]
        return redirect("/") 
            

    return render_template("register.html")    

@app.route("/login",methods = ["GET","POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        error = ""
        if not username:
            error = "Please enter valid user name"
        elif not password:
            error = "Please enter valid password"
        if error:
            return render_template("login.html",value = error)
        
        cursor.execute("select * from users where username = %s",(username,))
        results = cursor.fetchall()
        if not results :
            error = "Invalid username or password"
        elif not check_password_hash(results[0][2],password):
            error =  "Invalid username or password"
        if error:
            return render_template("login.html",value = error)
        session["id"] = results[0][0]
        return redirect("/") 
    return render_template("login.html")
            
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/")
def home():
    if not check_log():
        return render_template("login.html")
    action = ""
    source = request.args.get("source")
    if source == "/buy":
        action = "Bought!"
    elif source == "/sell":
        action =  "Sold!"
    elif source == '/addcash':
        action = 'Deposit completed successfully.'    

    cursor.execute("select cash from users where id = %s",(session["id"],))
    result = cursor.fetchall()
    cash = result[0][0]
    cursor.execute("select * from own_stocks where user_id = %s",(session["id"],))
    result = cursor.fetchall()
    full_total = 0
    for i in range(len(result)):
        stock = func.lookup(result[i][1])
        price = Decimal(stock["latestprice"])
        total = (f"${price * result[i][2]:,.2f}",)
        full_total += price * result[i][2]
        price = (f"${price:,.2f}",)
        result[i] += price + total        
    full_total += cash    
    return render_template("index.html",result = result,cash = f"${cash:,.2f}",full_total = f"${full_total:,.2f}",action = action)

@app.route("/buy",methods = ["GET","POST"])
def buy():
    if not check_log():
        return render_template("login.html")
    if request.method == "POST":
        error = ""
        symbol = request.form.get("symbol").upper()
        stock_info = func.lookup(symbol)
        if not symbol:
            error = "Enter valid symbol"
        elif not stock_info:
            error = "stock is not found"
        else:
            shares = func.check_positveint(request.form.get("shares"))
            if shares == -1:
                error = "Enter valid shares number"    
        
        if error:
            return render_template("buy.html",value = error)    
        total_cost = Decimal(shares * stock_info["latestprice"])
        cursor.execute("select cash from users where id = %s",(session["id"],))
        result = cursor.fetchall()
        cash = result[0][0]
        if cash< total_cost:
            error = "you don't have enough cash"
            return render_template("buy.html",value = error)     
        cash -= total_cost
        cursor.execute("update users set cash = %s where id = %s ",(cash,session["id"]))
        query = "insert into userstock(user_id,symbol,shares,price)values(%s,%s,%s,%s)"
        cursor.execute(query,(session["id"],stock_info["symbol"],shares,total_cost))
        ins.commit()
        return redirect(url_for("home",source = "/buy"))

    return render_template("buy.html")


@app.route("/sell",methods =["POST","GET"])
def sell():
    if not check_log():
        return render_template("login.html")    
    
    cursor.execute("select * from own_stocks where user_id = %s",(session["id"],))
    result = cursor.fetchall()
    error = {}
    item_found = False
    if request.method == "POST":
        try:
            symbol = request.form.get("symbol").upper()
        except:
            error['symbol'] = 'There is no provided symbol'
        shares = func.check_positveint(request.form.get("shares"))
        
        if shares == -1:
            error['shares']= "Enter valid shares number" 
        
        elif not error:
            for row in result:
                if symbol == row[1]:
                    item_found = True
                    if shares > row[2]:
                        error['shares'] = "you don't have this amount of this stock"
                        break
            if not item_found:        
               error['symbol'] = "You don't have this stock"    
                 
        if error:
            return render_template("sell.html",value = error,symbols = result)
        cursor.execute("select cash from users where id = %s",(session["id"],))
        result = cursor.fetchall()
        cash = result[0][0]
        stock_info = func.lookup(symbol)
        total_amount = Decimal(shares * stock_info["latestprice"])
        cash += total_amount
        cursor.execute("update users set cash = %s where id = %s ",(cash,session["id"]))
        query = "insert into userstock(user_id,symbol,shares,price)values(%s,%s,%s,%s)"
        cursor.execute(query,(session["id"],symbol,0 - shares,total_amount))
        ins.commit()
        return redirect(url_for("home",source = "/sell"))
    return render_template("sell.html",symbols = result,value = error) 

@app.route("/quote",methods = ["GET","POST"])
def quote():
    if not check_log():
        return render_template("login.html")

    if request.method == "POST":
        error = ""
        error_status = True
        symbol = request.form.get("symbol").upper()
        stock_info = func.lookup(symbol)
        if not symbol:
            error = "Enter valid symbol"
        elif not stock_info:
            error = "stock is not found"
        else:
            error_status = False
            error = f"current price of {symbol} is ${stock_info['latestprice']:,.2f} "
        return render_template("quote.html",value = error,error_status = error_status,symbol = symbol)
    else:
        return render_template("quote.html")

@app.route("/history")
def history():
    if not check_log():
        return render_template("login.html")
    cursor.execute("select * from userstock where user_id = %s",(session["id"],))
    result = cursor.fetchall()
    return render_template("history.html",result = result)

@app.route("/changepasswd",methods = ["GET","POST"])
def password():
    if not check_log():
        return render_template("login.html")
    if request.method == "POST":
        error = ""
        action = ''
        old = request.form.get("old")
        new = request.form.get("new")
        if not old or not new:
            error = "Please enter valid password"
        else:
            cursor.execute("select * from users where id = %s",(session["id"],))
            result = cursor.fetchall()
            if not check_password_hash(result[0][2],old):
                error = "Current password is not valid"
            else:
                query = "update users set hash = %s where id = %s"
                cursor.execute(query,(generate_password_hash(new),session["id"]))
                ins.commit()
                action = "Password changed  successfully!"
        return render_template("password.html",error = error,action = action)
    return render_template("password.html")            

@app.route("/addcash",methods = ["GET","POST"])
def add_cash():
    if not check_log():
        return render_template("login.html")
    if request.method == "POST":
        increase = request.form.get("amount")
        if func.check_positveint(increase) == -1:
            return render_template("addcash.html",error = "Enter valid amount") 
        cursor.execute("update users set cash = cash + %s where id = %s",(increase,session["id"]))
        ins.commit()
        return redirect("/?source=/addcash")
    return render_template("addcash.html")









            




def check_log():
    if not session.get("id"):
        return False
    return True          


    

    



        