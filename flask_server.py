from flask import Flask, request, render_template, jsonify, redirect, url_for, session, request, flash
from py_scripts import db_conn
from py_scripts.db_conn import conn_init, generate_otp, save_otp, send_otp_email, verifying_otp, update_password
from sqlalchemy import text

server = Flask(__name__)


@server.route('/')
def landing_page():
    return render_template('index.html')

# ========================== INDEX ==========================

@server.route('/index', methods=['POST'])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    sign_in = db_conn.sign_in(username, password)
    
    if sign_in == 'success':
        return redirect(url_for('home'))  
        return '''
        <script>
            alert("Invalid username or password! Try again.");
            window.location.href = "/";
        </script>
        '''  # Shows an alert and redirects back to login

@server.route('/home')
def home():
    return render_template('home.html')

@server.route('/members')
def members():
    return render_template('members.html')

@server.route('/create_account')
def create_account():
    return render_template('create_account.html')


server.secret_key = 'ifgms'  

# ========================== FORGOT PASSWORD ==========================
@server.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]

        otp = generate_otp()  # Generate OTP
        save_otp(email, otp)  # Save OTP in otp_verifications table
        send_otp_email(email, otp) # Send OTP to user's 

        session["email"] = email
        flash("OTP has been sent to your email.", "info")
        return redirect(url_for("verify_otp"))

    return render_template("forgot_password.html")

# ========================== VERIFY OTP ==========================
@server.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp(): 
    if request.method == 'POST':
        email = request.form.get('email')  # Get email from form
        otp_input = request.form.get('otp')  # Get OTP from form

        # Call the database function to verify OTP
        result = db_conn.verifying_otp(email, otp_input)

        if result == "success":
            flash({
                "title": "OTP Verified Successfully!",
                "text": "You can now proceed to reset your password.",
                "redirect_url": url_for('reset_password')
            }, "success")
            return redirect(url_for('reset_password'))  # Redirect to reset password page

        elif result == "expired":
            flash("OTP has expired. Please try again.", "error")  # Flash message for expired OTP
            return redirect(url_for('forgot_password'))  # Redirect to forgot password page

        elif result == "email_not_found":
            flash("This email is not registered. Please check your email or create an account.", "error")
            return redirect(url_for('forgot_password'))  # Redirect back to forgot password page

        else:
            flash("Invalid OTP. Please try again.", "error")  # Flash message for invalid OTP
            return redirect(url_for('verify_otp'))  # Stay on the verify OTP page for retry

    return render_template('verify_otp.html')  # Render OTP verification page

# ========================== RESET PASSWORD ==========================
@server.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    email = session.get("email")
    if not email:
        flash("Session expired. Please try again.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match. Please try again.", "error")
        else:
            update_password(email, new_password)  
            session.pop("email", None) 
            flash({
                "title": "Password Reset Successfully!",
                "text": "You can now log in with your new password.",
                "redirect_url": url_for('login')
            }, "success")
            return redirect(url_for("login"))  
        
    return render_template("reset_password.html")

if __name__ == '__main__':
    server.run(debug=True, use_reloader=True)
    
