from flask import Flask, request, render_template, redirect, url_for, flash
from py_scripts import db_conn, tools
from datetime import date
import os

server = Flask(__name__)
server.secret_key = os.urandom(24)

@server.route('/')
def landing_page():
    return render_template('index.html')

@server.route('/create_account')
def create_acc():
    return render_template('create_account.html')

@server.route('/create_acc_submit', methods=['POST'])
def create_acc_submit():
    user = request.form.get('username')
    passw = request.form.get('password')
    email = request.form.get('email')

    fname = request.form.get('fname').upper()
    mname = request.form.get('mname').upper()
    lname = request.form.get('lname').upper()
    suffix = request.form.get('suffix')

    bdate = request.form.get('bdate')
    contact = request.form.get('contact_no')

    acct_created = date.today().strftime("%Y-%m-%d")
    branch = request.form.get('branch')

    if (fname, mname, lname, suffix, bdate, contact, email, user, passw, branch):
        #print(fname, mname, lname, suffix, bdate, contact, email, user, passw, branch) #todo remove afer development
        hashed_pass = tools.hash_password(passw)

        db_conn.create_account(user=user, hashed_pass=hashed_pass, email=email, fname=fname, mname=mname, lname=lname,
                               suffix=suffix, bdate=bdate, contact=contact, acct_created=acct_created, branch=branch)
    else:
        pass

    flash({
        "title": "Account created successfully!",
        "text": "Click continue to go back to login screen.",
        "redirect_url": url_for('landing_page')
    }, "success")
    return render_template('create_account.html')

@server.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')


@server.route('/reset_pass_email', methods=['POST'])
def reset_pass_email():
    return render_template('members.html') #reset pass next page


@server.route('/login', methods=['POST'])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    sign_in = db_conn.sign_in(username, password)
    
    if sign_in == 'success':
        return redirect(url_for('home'))  # Redirect to home page on success
    else:
    #    return '''
     #   <script>
      #      alert("Invalid username/password or account not approved yet. Try again.");
       #     window.location.href = "/";
        #</script>
        #'''  # Shows an alert and redirects back to login

        flash({
            "title": "Login Error!",
            "text": "Wrong username/password or account not approved yet. Try again.",
            "redirect_url": url_for('landing_page')
        }, "error")
        return render_template('index.html')

@server.route('/home')
def home():
    return render_template('home.html')

@server.route('/members')
def members_page():
    return render_template('/members.html')


@server.route('/accounts')
def show_user_accounts():
    active_accounts = db_conn.get_user_accounts(status=['approved', 'archived', 'declined'])
    pending_accounts = db_conn.get_user_accounts(status=['pending'])

    return render_template('accounts.html', active_accounts=active_accounts, pending_accounts=pending_accounts)



if __name__ == '__main__':
    server.run(debug=True, use_reloader=True)
    
