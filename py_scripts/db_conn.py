import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session
import cryptography
from datetime import date, datetime, timedelta, timezone
from py_scripts import tools
import py_scripts.models as models
from random import randint
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


current_dir = Path(__file__).parent
parent_dir = current_dir.parent
env_loc = parent_dir/'creds.env'

print("ENV File Location:", env_loc)

load_dotenv(env_loc)

SQL_HOST = os.getenv('SQL_HOST')
SQL_USER = os.getenv('SQL_USER')
SQL_PASS = os.getenv('SQL_PASS')
SQL_DB = os.getenv('SQL_DB')

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# todo remove on deployment
# print(f'SQL CONNECTION DEBUG\nHost={SQL_HOST}\nUser={SQL_USER}\nPass={SQL_PASS}\nDB={SQL_DB}')


def conn_init():
    try:
        db_url = f"mysql+pymysql://{SQL_USER}:{SQL_PASS}@{SQL_HOST}/{SQL_DB}"
        engine = create_engine(db_url)
        conn = engine.connect()

        print('Database Connection Success')
        return conn
    except OperationalError:
        try:
            print('Database doesn\'t exist. Creating one...')
            engine = create_engine(f"mysql+pymysql://{SQL_USER}:{SQL_PASS}@{SQL_HOST}")
            db_init_script = Path(parent_dir/'sql/ifgms_db.sql')
            init_val_script = Path(parent_dir/'sql/init_data.sql')

            with engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {SQL_DB};"))
                print(f"Database '{SQL_DB}' created successfully!")

                # Function to execute SQL scripts
                def execute_sql_script(script_path, engine):
                    if script_path.exists():
                        with open(script_path, "r") as file:
                            sql_script = file.read()

                        print(f"Executing {script_path.name}...")
                        with engine.connect() as conn:
                            for statement in sql_script.split(";"):  # Split script into individual statements
                                statement = statement.strip()
                                if statement:  # Ignore empty statements
                                    conn.execute(text(statement))
                            conn.commit()
                        print(f"{script_path.name} executed successfully!")
                    else:
                        print(f"SQL script '{script_path}' not found!")

                # Reconnect with the new database
                db_url_with_db = f"mysql+pymysql://{SQL_USER}:{SQL_PASS}@{SQL_HOST}/{SQL_DB}"
                engine_with_db = create_engine(db_url_with_db)

                # Execute both SQL scripts
                execute_sql_script(db_init_script, engine_with_db)
                execute_sql_script(init_val_script, engine_with_db)

                # Final connection
                conn = engine_with_db.connect()
                print("Database connection successful!")
                return conn
        except Exception as e:
            print(f"Error: {e}")


def create_account(**kwargs):
    """ arguments must be the same name as in the sql query """
    conn = conn_init()

    try:
        with conn.begin():
            query = text(f"INSERT INTO accounts VALUES"
                         " (NULL, :user, :hashed_pass, :email, :fname, :mname, :lname, :suffix,"
                         " :bdate, :contact, :acct_created, :branch, DEFAULT, DEFAULT, NULL)")
            conn.execute(query, kwargs)
            conn.commit()
    except Exception as e:
        print(f"Error: {e}")


def sign_in(username=None, password=None):
    conn = conn_init()
    Session = sessionmaker(bind=conn)

    with Session() as session:
        query = text("SELECT password, acct_status FROM accounts WHERE username = :username AND (acct_status = 'approved' OR acct_status = 'pending')")
        result = session.execute(query, {"username": username}).fetchone()

    if result and tools.check_password(password, result[0]) and result[1] == 'approved':
        return 'success'
    elif result and tools.check_password(password, result[0]) and result[1] == 'pending':
        return 'pending'
    else:
        return 'fail'

def get_user_accounts(status):
    conn = conn_init()

    with conn:
        query = text("SELECT * FROM accounts WHERE acct_status IN :status")
        result = conn.execute(query, {'status': tuple(status)})
        accounts = result.fetchall()
        return accounts

def account_action(selected_ids, action):    
    Session = sessionmaker(bind=conn_init())
    session = Session()
    
    try:
        affected_accounts = session.query(models.Accounts).filter(models.Accounts.account_id.in_(selected_ids)).all()
        
        if action == 'create':
            pass
        elif action == 'archive':
            for account in affected_accounts:
                account.acct_status = 'archived'
                session.add(account)
        elif action == 'reset':
            for account in affected_accounts:          
                if account.birth_date:
                    bdate = str(account.birth_date).replace('-', '')
                else:
                    bdate = '00000000'
                initials = (account.first_name[:1] + account.middle_name[:1] + account.last_name[:1]).lower().strip()
       
                reset_pass = bdate + initials
                print(reset_pass)
                hashed_pass = tools.hash_password(reset_pass)
                    
                account.password = hashed_pass
                session.add(account)            
        elif action == 'approve':
            for account in affected_accounts:
                account.acct_status = 'approved'
                session.add(account)
        elif action == 'decline':
            for account in affected_accounts:
                account.acct_status = 'declined'
                session.add(account)
            
            
            
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close
    return None
    
# ? RESET PASS START
# !!!!!!!!!!!!!!!!!!!!!!!! GENERATE OTP !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
def generate_otp():
    """Generate a random 6-digit OTP."""
    return str(randint(100000, 999999))


# !!!!!!!!!!!!!!!!!!!!!!!! SAVE OTP !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
def save_otp(email, otp):
    """Save OTP in the database with expiration time."""
    conn = conn_init()
    Session = sessionmaker(bind=conn)
    expires_at = datetime.now() + timedelta(minutes=5)
    created_at = datetime.now()  # Capture the time when OTP is generated
    
    with Session() as session:
        query = text("""
            INSERT INTO otp_verifications (email, otp, expires_at, created_at) 
            VALUES (:email, :otp, :expires_at, :created_at)
        """)
        session.execute(query, {
            "email": email,
            "otp": otp,
            "expires_at": expires_at,
            "created_at": created_at
        })
        session.commit()


# !!!!!!!!!!!!!!!!!!!!!!!! SEND OTP !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
def send_otp_email(email, otp):
    """Send OTP to the user's email."""
    subject = "Your OTP Code"
    body = f"Your OTP code is: {otp}. It will expire in 5 minutes."

    message = MIMEMultipart()
    message['From'] = SENDER_EMAIL
    message['To'] = email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, message.as_string())
        print("OTP sent successfully!")
    except Exception as e:
        print(f"Failed to send OTP: {e}")


# !!!!!!!!!!!!!!!!!!!!!!!! VERIFY OTP !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
def verifying_otp(email, otp_input):
    """Verify OTP against the database (original version with added debug prints)"""
    print(f"[DEBUG] Starting OTP verification for {email}")
    print(f"[DEBUG] Input OTP: {otp_input} (type: {type(otp_input)})")
    
    conn = conn_init()
    if not conn:
        print("[ERROR] Connection failed!")
        return "fail"

    Session = sessionmaker(bind=conn)

    with Session() as session:
        query = text("SELECT otp, expires_at FROM otp_verifications WHERE email = :email ORDER BY created_at DESC LIMIT 1")
        result = session.execute(query, {"email": email}).fetchone()
        print(f"[DEBUG] Database query result: {result}")

    if result:
        otp, expires_at = result
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        current_time = datetime.now(timezone.utc)
        print(f"[DEBUG] Stored OTP: {otp} (type: {type(otp)})")
        print(f"[DEBUG] Expires at: {expires_at}")
        print(f"[DEBUG] Current time: {current_time}")

        if current_time > expires_at:
            print("[DEBUG] OTP expired")
            return "expired"
        
        if str(otp_input) == str(otp):
            print("[DEBUG] OTP matched")
            delete_query = text("DELETE FROM otp_verifications WHERE email = :email")
            with Session() as session:
                session.execute(delete_query, {"email": email})
                session.commit()
            return "success"
        else:
            print("[DEBUG] OTP mismatch")
            return "fail"
    else:
        print("[DEBUG] No OTP found for this email")
        return "fail"
    
    
def update_password(email, new_password):
    """Update the password in the database."""
    conn = conn_init()
    Session = sessionmaker(bind=conn)

    salted_pass = tools.hash_password(new_password)

    with Session() as session:
        query = text("UPDATE accounts SET password = :new_password WHERE email = :email")
        session.execute(query, {"new_password": salted_pass, "email": email})
        session.commit()

# ? RESET PASS END


def get_member_records():
    conn = conn_init()

    with conn:
        query = text("SELECT * FROM membership_records")
        result = conn.execute(query)
        records = result.fetchall()
        return records


def get_claim_records():
    conn = conn_init()
    with conn:
        query = text("""
            SELECT
                mc.*,
                mr.effectivity_date,
                mi.first_name,
                mi.middle_name,
                mi.last_name,
                mi.suffix,
                mi.contact_no,
                mi.email
            FROM maab_claims mc
            LEFT JOIN entry_contents ec ON mc.maab_no = ec.maab_no
            LEFT JOIN membership_records mr ON ec.record_id = mr.record_id
            LEFT JOIN members_info mi ON ec.member_id = mi.member_id
        """)
        result = conn.execute(query)
        records = result.fetchall()
        return records


def add_new_record():
    conn = conn_init()
    Session = sessionmaker(bind=conn)
    with Session() as session:
        new_record = models.Records(
            year=datetime.now().year,
            id_received=None,
            declared=None,
            declaration_date=None,
            effectivity_date=None,
            location_particular=None,
            location_category=None,
            municipality=None,
            district=None,
            paid=None,
            origin=None,
            remarks=None,
            tags=None
        )
        session.add(new_record)
        session.commit()
        return new_record.record_id


def add_claim_record():
    conn = conn_init()
    Session = sessionmaker(bind=conn)
    with Session() as session:
        new_claim_record = models.Claims(
            status='pending'
        )
        session.add(new_claim_record)
        session.commit()
        return new_claim_record.claim_id


def save_record_details(data):
    conn = conn_init()
    Session = sessionmaker(bind=conn)
    with Session() as session:
        record = session.query(models.Records).filter_by(record_id=data['record_id']).first()
        if not record:
            return False  # Or raise an exception

        # Update fields if present in data
        for field in [
            'year', 'id_received', 'declared', 'declaration_date', 'effectivity_date',
            'location_particular', 'location_category', 'municipality', 'district',
            'paid', 'origin', 'remarks', 'tags'
        ]:
            if field in data:
                value = data[field]
                # Convert empty string to None for ENUM/NULL columns
                if value == '':
                    value = None
                setattr(record, field, value)

        session.commit()
        return True


def get_entries(record_id):
    conn = conn_init()
    Session = sessionmaker(bind=conn)
    with Session() as session:
        # Join Entries and Members on member_id
        results = (
            session.query(
                models.Entries.entry_id,
                models.Entries.maab_category,
                models.Entries.maab_no,
                models.Members.first_name,
                models.Members.middle_name,
                models.Members.last_name,
                models.Members.suffix,
                models.Members.birth_date,
                models.Members.age,
                models.Members.sex,
                models.Members.contact_no,
                models.Members.email,
                models.Members.address,
                models.Members.blood_type,
                models.Entries.id_received,
                models.Entries.declared,
                models.Entries.declaration_date,
                models.Entries.paid,
                models.Entries.OR_num,
                models.Entries.OR_date,
                models.Entries.remarks,
                models.Entries.tags
            )
            .join(models.Members, models.Entries.member_id == models.Members.member_id)
            .filter(models.Entries.record_id == record_id)
            .all()
        )

        # Convert results to list of dicts
        col_names = [
            'entry_id', 'maab_category', 'maab_no', 'first_name', 'middle_name', 'last_name', 'suffix',
            'birth_date', 'age', 'sex', 'contact_no', 'email', 'address', 'blood_type', 'id_received',
            'declared', 'declaration_date', 'paid', 'OR_num', 'OR_date', 'remarks', 'tags'
        ]
        return [dict(zip(col_names, row)) for row in results]


def get_user_details_by_username(username):
    """
    Fetch user details from the database by username.
    :param username: username to search for
    :return: user details as dict or None if not found
    """
    conn = conn_init()
    Session = sessionmaker(bind=conn)

    with Session() as session:
        query = text("""
            SELECT first_name, middle_name, last_name, email, contact_no, birth_date, password, user_level
            FROM accounts 
            WHERE username = :username LIMIT 1
        """)
        result = session.execute(query, {"username": username}).fetchone()

    if result:
        # Convert the result to a dictionary
        return {
            "first_name": result[0],
            "middle_name": result[1],
            "last_name": result[2],
            "email": result[3],
            "contact_no": result[4],
            "birth_date": result[5].strftime("%Y-%m-%d") if result[5] else None,
            "password": result[6],
            "user_level": result[7]
        }
    else:
        print(f"No user found with username: {username}")
        return None


def get_inventory_entries(allocated_to=None):
    # Initialize connection
    conn = conn_init()

    # Create session
    Session = sessionmaker(bind=conn)
    with Session() as session:
        # Query inventory table with optional filter on 'allocated_to'
        query = session.query(
            models.Inventory.inv_id,
            models.Inventory.maab_category,
            models.Inventory.maab_no,
            models.Inventory.used,
            models.Inventory.remarks,
            models.Inventory.allocated_to
        )

        # Apply filter if 'allocated_to' is provided
        if allocated_to:
            query = query.filter(models.Inventory.allocated_to == allocated_to)

        # Fetch all results
        results = query.all()

        # Check if any results were returned
        if not results:
            print("No inventory data found.")
        
        # Convert results to list of dictionaries
        col_names = [
            'inv_id', 'maab_category', 'maab_no', 'used', 'remarks', 'allocated_to'
        ]
        return [dict(zip(col_names, row)) for row in results]


if __name__ == '__main__':
    conn_init()
    
    