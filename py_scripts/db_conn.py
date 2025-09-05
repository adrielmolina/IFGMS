import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text, func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, scoped_session
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

DB_CONNECTION_MODE = os.getenv('DB_CONNECTION_MODE', 'local').lower()

# FOR AIVEN DB CONNECTION
AIVEN_URI = os.getenv('AIVEN_URI')

# FOR LOCAL DB CONNECTION
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
        if DB_CONNECTION_MODE == "aiven":
            ca_path = Path(__file__).resolve().parent.parent / "sql" / "aiven" / "ca.pem"
            if not ca_path.exists():
                raise FileNotFoundError(f"SSL certificate not found: {ca_path}")
            
            db_url = f"{AIVEN_URI}&ssl_ca={ca_path}"
            print(f"Connecting to Aiven DB")
        
        else:  # local connection
            db_url = f"mysql+pymysql://{SQL_USER}:{SQL_PASS}@{SQL_HOST}/{SQL_DB}"
            print(f"Connecting to local DB")
            
        engine = create_engine(db_url, pool_pre_ping=True)
        print('Database Connection Success')
        return engine
    
    except OperationalError as e:
        print(f"Database Connection Failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return None
    

# TODO replace all session binds with SessionLocal
conn = conn_init()
SessionLocal = scoped_session(sessionmaker(bind=conn))
# db_session = SessionLocal() # Use this for queries


def shutdown_session():
    """Remove session (for Flask teardown)"""
    SessionLocal.remove()


def load_user(user_id):
    db_session = SessionLocal()
    return db_session.query(models.Accounts).get(int(user_id))


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
    db_session = SessionLocal()

    user = db_session.query(models.Accounts).filter(
        models.Accounts.username == username,
        models.Accounts.acct_status.in_(["approved", "pending"])
    ).first()

    if user and tools.check_password(password, user.password):
        return user  # return full user object instead of "success/pending/fail"
    return None
    
    

def get_user_accounts(status):
    db_session = SessionLocal()
    try:
        accounts = (
            db_session.query(models.Accounts)
            .filter(models.Accounts.acct_status.in_(status))
            .all()
        )
        return accounts
    finally:
        db_session.close()

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


def get_pending_claims_count():
    conn = conn_init()
    Session = sessionmaker(bind=conn)
    with Session() as session:
        count_pending = (
            session.query(func.count(models.Claims.claim_id))
            .filter(models.Claims.status == "pending")
            .scalar()
        )

    return count_pending



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


def verify_maab_no(maab_no):
    conn = conn_init()
    Session = sessionmaker(bind=conn)

    with Session() as session:
        # Check if maab_no exists and get member_id
        query = text("SELECT member_id, record_id FROM entry_contents WHERE maab_no = :maab_no")
        result = session.execute(query, {"maab_no": maab_no}).fetchone()

        if not result:
            return None  # maab_no does not exist
        else:
            record_id = result[1]
            query = text("SELECT effectivity_date FROM membership_records WHERE record_id = :record_id")
            record = session.execute(query, {"record_id": record_id}).fetchone()
            effectivity_date = record[0] if record else None

        member_id = result[0]

        # Get name fields from members_info
        query = text("""
            SELECT first_name, middle_name, last_name, suffix, contact_no, email
            FROM members_info
            WHERE member_id = :member_id
        """)
        member = session.execute(query, {"member_id": member_id}).fetchone()

        if member:
            return {
                "exists": True,
                "effectivity_date": effectivity_date.isoformat() if effectivity_date else None,
                "first_name": member[0],
                "middle_name": member[1],
                "last_name": member[2],
                "suffix": member[3],
                "contact_no": member[4],
                "email": member[5]
            }
        else:
            return {"exists": False, "effectivity_date": None, "first_name": None, "middle_name": None, "last_name": None, "suffix": None}

# TODO add indexes on fields that are frequently queried
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

# TODO add the new fields here to update
# TODO change the column 'status' to claim_status
# TODO change all instance of enhanced platinum to safe card
def save_claim_record(data):
    '''conn = conn_init()
    Session = sessionmaker(bind=conn)
    with Session() as session:
        claim = session.query(models.Claims).filter_by(claim_id=data['claim_id']).first()
        if not claim:
            return False  # Or raise an exception

        # List of all fields to update
        fields = [
            'date_filed', 'received_by', 'claim_origin', 'date_of_loss', 'maab_no',
            'same_as_insured', 'claimant_first_name', 'claimant_middle_name', 'claimant_last_name',
            'claimant_suffix', 'relation_to_insured', 'claimant_contact_no', 'claimant_email',
            'claim_remarks', 'status', 'date_released', 'chinabank_check_no', 'chinabank_amount',
            'bpi_check_no', 'bpi_amount', 'release_remarks', 'scanned_docs', 'prm_file',
            'quit_claim_file', 'picked_up', 'date_picked_up', 'req_claim_form', 'req_prc_id',
            'req_med_cert', 'req_hos_bill_or', 'req_state_of_acc', 'req_doctor_pres',
            'req_purchased_meds', 'req_med_records', 'req_incident_rep', 'req_police_rep',
            'req_drivers_lic', 'sent_advanced_notice'
        ]

        for field in fields:
            if field in data:
                value = data[field]
                # Convert empty string to None for nullable columns
                if value == '':
                    value = None
                setattr(claim, field, value)

        session.commit()
        return True'''
    # TODO check if this works properly then delete above code. check if each field is saving
    conn = conn_init()
    Session = sessionmaker(bind=conn)
    with Session() as session:
        claim = session.query(models.Claims).filter_by(claim_id=data.get('claim_id')).first()
        if not claim:
            return False  # or raise Exception("Claim not found")

        # Get list of column names directly from the ORM model
        model_columns = {col.name for col in models.Claims.__table__.columns}

        for field, value in data.items():
            if field in model_columns and field != "claim_id":  # don't overwrite PK
                setattr(claim, field, value or None)  # empty string → None

        session.commit()
        return True


def delete_claim_record(claim_id):
    conn = conn_init()
    Session = sessionmaker(bind=conn)
    with Session() as session:
        claim = session.query(models.Claims).get(claim_id)
        if not claim:
            return False

        try:
            # Get all column names from Claims_Archive except PK and extra columns
            archive_columns = [
                col.name for col in models.Claims_Archive.__table__.columns
                if col.name != ("archived_claim_id",)  # Exclude PK or auto fields
            ]

            # Create a dict of column:value from the Claims record
            claim_data = {
                col: getattr(claim, col)
                for col in archive_columns
                if hasattr(claim, col)
            }

            # Create archive record dynamically
            archived_claim = models.Claims_Archive(**claim_data)

            session.add(archived_claim)
            session.delete(claim)
            session.commit()
            return True

        except Exception as e:
            session.rollback()
            print(f"Error deleting claim: {e}")
            return False


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

# ! TODO remove this function. THIS FUNCTION IS RETIRED
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
    print('do no run this module directly lol')
    print('use initialize_database.py')
    
    