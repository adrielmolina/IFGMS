import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import create_engine, text, func, extract, distinct
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
import resend

if os.getenv('FLASK_ENV') == 'production' or os.getenv('FLASK_ENV') == 'development':
    DB_CONNECTION_MODE = os.getenv('DB_CONNECTION_MODE', 'aiven').lower()
else:
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    env_loc = parent_dir/'creds.env'

    load_dotenv(env_loc)

    DB_CONNECTION_MODE = os.getenv('DB_CONNECTION_MODE', 'local').lower()

# FOR AIVEN DB CONNECTION
AIVEN_URI = os.getenv('AIVEN_URI')

# FOR RAILWAY DB CONNECTION
RAILWAY_URI = os.getenv('RAILWAY_URI')

# FOR LOCAL DB CONNECTION
SQL_HOST = os.getenv('SQL_HOST')
SQL_USER = os.getenv('SQL_USER')
SQL_PASS = os.getenv('SQL_PASS')
SQL_DB = os.getenv('SQL_DB')

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

RESEND_SENDER_EMAIL = os.getenv("RESEND_SENDER_EMAIL")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

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
        
        elif DB_CONNECTION_MODE == "railway":
            # Convert mysql:// to mysql+pymysql:// for SQLAlchemy
            formatted_url = RAILWAY_URI.replace("mysql://", "mysql+pymysql://")
            db_url = formatted_url
            print("Connecting to Railway DB")
        
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


def sign_in(username=None, password=None):    
    db_session = SessionLocal()
    
    try:
        user = db_session.query(models.Accounts).filter(
            models.Accounts.username == username,
            models.Accounts.acct_status.in_(["approved", "pending"])
        ).first()

        print(f"🔍 DEBUG sign_in: username='{username}', user_found={user is not None}")

        if user and tools.check_password(password, user.password):
            print(f"🔍 DEBUG: Password correct for user {username}")
            # Expunge the user from the session so it becomes detached but usable
            db_session.expunge(user)
            db_session.close()
            return user
        else:
            print(f"🔍 DEBUG: Invalid credentials for user {username}")
            db_session.close()
            return None
            
    except Exception as e:
        print(f"❌ Error in sign_in: {e}")
        db_session.close()
        return None
    
    
# TODO make the generated id current year + 0000 + last inserted id
def create_account(**kwargs):
    """ arguments must be the same name as in the sql query """
    
    db_session = SessionLocal()
    
    hashed_pass = tools.hash_password(kwargs.get('password'))
    try:
        new_account = models.Accounts(
            username=kwargs.get('user'),
            password=hashed_pass,
            email=kwargs.get('email'),
            first_name=kwargs.get('fname'),
            middle_name=kwargs.get('mname'),
            last_name=kwargs.get('lname'),
            suffix=kwargs.get('suffix'),
            birth_date=kwargs.get('bdate'),
            contact_no=kwargs.get('contact'),
            acct_created=kwargs.get('acct_created'),
            office_location=kwargs.get('branch'),
            user_level='staff',  # default user level
            acct_status='approved',  # default status
            acct_review_date=None  # default review date
        )
        db_session.add(new_account)
        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        print(f"Error creating account: {e}")
        return str(e)
# Add these to your db_conn class if they don't exist
def username_exists(self, username):
    """Check if username already exists in database"""
    try:
        # If you're using SQLAlchemy
        db_session = SessionLocal()
        existing_user = db_session.query(models.Accounts).filter(
            models.Accounts.username == username
        ).first()
        db_session.close()
        return existing_user is not None
    except Exception as e:
        print(f"Error in username_exists: {e}")
        return False

def email_exists(self, email):
    """Check if email already exists in database"""
    if not email:
        return False
    try:
        db_session = SessionLocal()
        existing_email = db_session.query(models.Accounts).filter(
            models.Accounts.email == email
        ).first()
        db_session.close()
        return existing_email is not None
    except Exception as e:
        print(f"Error in email_exists: {e}")
        return False

# ADD THESE FUNCTIONS TO YOUR db_conn.py

def archive_account_to_table(account_id, archived_by_id):
    """
    Simple archive - just update account status to 'archived'
    """
    db_session = SessionLocal()
    try:
        print(f"🔄 Archiving account {account_id}...")
        
        # Direct update without fetching the object first
        result = db_session.query(models.Accounts).filter(
            models.Accounts.account_id == account_id
        ).update({
            models.Accounts.acct_status: 'archived'
        })
        
        db_session.commit()
        
        if result > 0:
            print(f"✅ Successfully archived account {account_id}")
            
            # Try to log, but don't fail if logging fails
            try:
                archiver = db_session.query(models.Accounts).filter(
                    models.Accounts.account_id == archived_by_id
                ).first()
                
                if archiver:
                    POST_action_log(
                        archiver.username,
                        archiver.user_level,
                        "Archive Account",
                        f"Archived account ID: {account_id}",
                        archived_by_id
                    )
            except Exception as log_error:
                print(f"⚠️ Logging failed but archive succeeded: {log_error}")
            
            return True
        else:
            print(f"❌ Account {account_id} not found")
            return False
            
    except Exception as e:
        print(f"❌ Error archiving account {account_id}: {e}")
        db_session.rollback()
        return False
    finally:
        db_session.close()

def name_exists(fname, lname, mname=None):
    """Check if name combination already exists in database"""
    try:
        db_session = SessionLocal()
        query = db_session.query(models.Accounts).filter(
            models.Accounts.first_name == fname,
            models.Accounts.last_name == lname
        )
        if mname and mname.strip():
            query = query.filter(models.Accounts.middle_name == mname)
        else:
            query = query.filter(
                (models.Accounts.middle_name == '') | 
                (models.Accounts.middle_name.is_(None))
            )
        
        existing_user = query.first()
        return existing_user is not None
    except Exception as e:
        print(f"Error checking name existence: {e}")
        return False
    finally:
        db_session.close()

def name_exists(fname, lname, mname=None):
    """Check if name combination already exists in database"""
    try:
        db_session = SessionLocal()
        query = db_session.query(models.Accounts).filter(
            models.Accounts.first_name == fname,
            models.Accounts.last_name == lname
        )
        if mname and mname.strip():
            query = query.filter(models.Accounts.middle_name == mname)
        else:
            query = query.filter(
                (models.Accounts.middle_name == '') | 
                (models.Accounts.middle_name.is_(None))
            )
        
        existing_user = query.first()
        return existing_user is not None
    except Exception as e:
        print(f"Error checking name existence: {e}")
        return False
    finally:
        db_session.close()
  
    
def save_otp(email, otp):
    """Save OTP in the database with expiration time."""
    
    db_session = SessionLocal()
    
    expires_at = datetime.now() + timedelta(minutes=5)
    created_at = datetime.now()

    try:
        new_otp = models.OTPs(
            email=email,
            otp=otp,
            expires_at=expires_at,
            created_at=created_at,
            otp_used=False  # default value, but explicit for clarity
        )
        db_session.add(new_otp)
        db_session.commit()
        return 'success'
    except Exception as e:
        db_session.rollback()
        print(f"Error saving OTP: {e}")
        raise
    
# TODO update email icon

# Set API key
resend.api_key = RESEND_API_KEY
def send_otp_email(email, otp):
    
    """Send OTP to the user's email using Resend API."""
    subject = "Your OTP Code for Password Reset"

    # Same message as before, but wrapped in light HTML styling
    html_body = f"""
    <div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
        <p>Your OTP code for <strong>FGMS</strong> password reset is: <strong>{otp}</strong></p>
        <p style="color: #555;">This OTP will expire in 5 minutes.</p>
        <p>If you didn't request this password reset, please ignore this email.</p>
        <br>
        <p>Thank you,<br><strong>FGMS Team</strong></p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": RESEND_SENDER_EMAIL,
            "to": email,
            "subject": subject,
            "html": html_body
        })
        print("✅ OTP sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to send OTP: {e}")
        return False
    
    # OLD SMTP METHOD
    '''
    
    """Send OTP to the user's email. Returns True if successful, False otherwise."""
    subject = "Your OTP Code for Password Reset"
    body = f"""
    Your OTP code for FGMS password reset is: {otp}
    
    This OTP will expire in 5 minutes.
    
    If you didn't request this password reset, please ignore this email.
    
    Thank you,
    FGMS Team
    """

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
        print("✅ OTP sent successfully!")
        return True  # ✅ CRITICAL: Return True on success
    except Exception as e:
        print(f"❌ Failed to send OTP: {e}")
        return False  # Return False on failure
    '''
    
    

def verifying_otp(email, otp_input):
    """Verify OTP against the database (original version with added debug prints)"""
    print(f"[DEBUG] Starting OTP verification for {email}")
    print(f"[DEBUG] Input OTP: {otp_input} (type: {type(otp_input)})")
    db_session = SessionLocal()
    
    try:
        # Get the most recent OTP for this email
        latest_otp = (
            db_session.query(models.OTPs)
            .filter_by(email=email)
            .order_by(models.OTPs.created_at.desc())
            .first()
        )
        
        if not latest_otp:
            print("[DEBUG] No OTP found for this email")
            return "email_not_found"
        
        # Check if OTP is already used
        if latest_otp.otp_used:
            print("[DEBUG] OTP already used")
            return "already_used"

        print(f"[DEBUG] Stored OTP: {latest_otp.otp}")
        print(f"[DEBUG] Expires at: {latest_otp.expires_at}")
        print(f"[DEBUG] Current time: {datetime.now(timezone.utc)}")

        # Check if expired
        if datetime.now(timezone.utc) > latest_otp.expires_at.replace(tzinfo=timezone.utc):
            print("[DEBUG] OTP expired")
            return "expired"

        # Check if matches
        if str(otp_input) == str(latest_otp.otp):
            print("[DEBUG] OTP matched")

            # Delete all OTPs for this email
            db_session.query(models.OTPs).filter_by(email=email).update({models.OTPs.otp_used: 1})
            db_session.commit()
            return "success"
        else:
            print("[DEBUG] OTP mismatch")
            return "fail"
        
    except Exception as e:
        db_session.rollback()
        print(f"[ERROR] verifying_otp: {e}")
        return "fail"
        
    
    '''
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
    '''
    
# TODO continue the ORM syntax update from here    
def update_password(email, new_password):
    """Update the password in the database. Returns True if successful, False otherwise."""
    db_session = SessionLocal()
    try:
        salted_pass = tools.hash_password(new_password)

        # Update using SQLAlchemy ORM
        user = db_session.query(models.Accounts).filter(
            models.Accounts.email == email
        ).first()
        
        if user:
            user.password = salted_pass
            db_session.commit()
            print(f"✅ Password updated successfully for {email}")
            return True
        else:
            print(f"❌ User with email {email} not found")
            return False
            
    except Exception as e:
        db_session.rollback()
        print(f"❌ Error updating password: {e}")
        return False
    finally:
        db_session.close()
# ? RESET PASS END    
    


def create_dispatch(dispatch_type, origin, year, cutoff, late, remarks):
    db_session = SessionLocal()
    try:
        print(f"🎯 Creating dispatch in database:")
        print(f"   Type: {dispatch_type}")
        print(f"   Origin: {origin}")
        print(f"   Year: {year}")
        print(f"   Cutoff: {cutoff}")
        print(f"   Late Declare: {late}")
        print(f"   Remarks: {remarks}")
        
        new_dispatch = models.Dispatch(
            dispatch_type=dispatch_type,
            dispatch_origin=origin,
            dispatch_year=year,
            dispatch_cutoff=cutoff,
            late_declare=late,
            dispatch_remarks=remarks,
            dispatch_status='current'  # Make sure this is set
        )
        db_session.add(new_dispatch)
        db_session.commit()
        
        print(f"✅ Dispatch created successfully with ID: {new_dispatch.dispatch_id}")
        return True
    except Exception as e:
        db_session.rollback()
        print(f"❌ Error creating dispatch: {e}")
        import traceback
        traceback.print_exc()
        return str(e)


def check_active_dispatch():
    """Check if there's an active dispatch and return its ID"""
    db_session = SessionLocal()
    try:
        active_dispatch = get_current_active_dispatch()
        return {
            'has_active_dispatch': active_dispatch is not None,
            'dispatch_id': active_dispatch.dispatch_id if active_dispatch else None
        }
    except Exception as e:
        print(f"Error checking active dispatch: {e}")
        return {'has_active_dispatch': False}
    finally:
        db_session.close()






def get_accounts(status):
    ''' for account module '''
    
    db_session = SessionLocal()
    try:
        accounts = (
            db_session.query(models.Accounts)
            .filter(models.Accounts.acct_status.in_(status))
            .all()
        )
        return accounts
    
    except Exception as e:
        print(f"Error fetching accounts: {e}")
        return []


def approve_account(id):
    db_session = SessionLocal()
    try:
        account = db_session.query(models.Accounts).filter_by(account_id=id).first()
        if account:
            account.acct_status = 'approved'
            account.acct_review_date = datetime.now()
            db_session.commit()
            return True
        return False
    except Exception as e:
        db_session.rollback()
        print(f"Error approving account: {e}")
        return False
    

def decline_account(id):
    db_session = SessionLocal()
    try:
        account = db_session.query(models.Accounts).filter_by(account_id=id).first()
        if account:
            account.acct_status = 'declined'
            account.acct_review_date = datetime.now()
            db_session.commit()
            return True
        return False
    except Exception as e:
        db_session.rollback()
        print(f"Error approving account: {e}")
        return False


def reset_account(id):
    db_session = SessionLocal()
    try:
        account = db_session.query(models.Accounts).filter_by(account_id=id).first()
        if account:
            print(f"=== RESET PASSWORD DEBUG ===")
            print(f"Account: {account.first_name} {account.last_name}")
            print(f"Birthdate: {account.birth_date}")
            
            # Generate new password
            from datetime import datetime
            now = datetime.now()
            current_year = now.year
            current_month = str(now.month).zfill(2)
            initials = (account.first_name[0] + account.last_name[0]).upper()
            
            new_password = f"{current_year}{current_month}{initials}"
            print(f"New password: {new_password}")
            
            # Hash the password
            hashed_password = tools.hash_password(new_password)
            print(f"Password hashed: {len(hashed_password)} characters")
            
            # Update the account
            account.password = hashed_password
            db_session.commit()
            
            print(f"✅ Password reset successful!")
            return True
        else:
            print(f"❌ Account {id} not found")
            return False
            
    except Exception as e:
        print(f"❌ Error in reset_account: {e}")
        import traceback
        traceback.print_exc()
        db_session.rollback()
        return False
    finally:
        db_session.close()


def update_userlvl(id, new_level):
    db_session = SessionLocal()
    try:
        account = db_session.query(models.Accounts).filter_by(account_id=id).first()
        if account:
            print(f"Updating user level for account ID {id} to {new_level}")
            account.user_level = new_level
            db_session.commit()
            return True
        return False
    except Exception as e:
        db_session.rollback()
        print(f"Error approving account: {e}")
        return False


def update_ofc(id, new_ofc):
    db_session = SessionLocal()
    try:
        account = db_session.query(models.Accounts).filter_by(account_id=id).first()
        if account:
            print(f"Updating office location for account ID {id} to {new_ofc}")
            account.office_location = new_ofc
            db_session.commit()
            return True
        return False
    except Exception as e:
        db_session.rollback()
        print(f"Error approving account: {e}")
        return False


def archive_account(id):
    db_session = SessionLocal()
    try:
        account = db_session.query(models.Accounts).filter_by(account_id=id).first()
        if account:
            account.acct_status = 'archived'
            db_session.commit()
            return True
        return False
    except Exception as e:
        db_session.rollback()
        print(f"Error approving account: {e}")
        return False



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


'''
# MERGE CONFLICT AREA START

def get_member_records(status='active', office_loc=None):
    """
    Get member records with optional status filter
    """
    db_session = SessionLocal()
    try:
        print(f"DEBUG: Querying database for status: {status}")
        
        # Use the correct model name - check if it's Records or MemberRecords
        # Try Records first (based on your add_new_record function)
        query = db_session.query(models.Records)
        
        if status:
            query = query.filter(models.Records.status == status)
        
        records = query.order_by(models.Records.record_id.desc()).all()
        print(f"DEBUG: Found {len(records)} records")
        return records
        
    except Exception as e:
        print(f"DEBUG: Error in get_member_records: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db_session.close()
        
# TODO fix this after merge        
def get_member_records(office_loc):
    db_session = SessionLocal()
    try:
        if office_loc == 'Chapter':
        # Chapter = all Chapter + declared Dasmariñas/Silang
            records = (
                db_session.query(models.Records)
                .filter(
                    (models.Records.origin == "Chapter") |
                    ((models.Records.origin.in_(["Dasmariñas", "Silang"])) &
                    (models.Records.tags == "transmitted"))
                )
                .order_by(models.Records.record_id.desc())
                .all()
            )

        elif office_loc == 'Dasmarinas':
            # Only Dasmariñas
            records = (
                db_session.query(models.Records)
                .filter(models.Records.origin == "Dasmariñas")
                .order_by(models.Records.record_id.desc())
                .all()
            )

        elif office_loc == 'Silang':
            # Only Silang
            records = (
                db_session.query(models.Records)
                .filter(models.Records.origin == "Silang")
                .order_by(models.Records.record_id.desc())
                .all()
            )

        return records

    except Exception as e:
        return f"Error fetching member records: {e}"
    

MERGE CONFLICT AREA END
'''    
    
    
'''
        query = text("SELECT * FROM membership_records")
        result = conn.execute(query)
        records = result.fetchall()
        return records
    '''
    
    
def get_member_records(status='active', office_loc=None):
    """
    Get member records filtered by office location and optional status.
    """
    db_session = SessionLocal()
    try:
        # Base query
        query = db_session.query(models.Records)

        # Apply status filter if provided
        if status:
            query = query.filter(models.Records.status == status)

        # Apply office location logic
        if office_loc == 'Chapter':
            # Chapter users can see all records
            print("🔍 Chapter user - showing all records")
            # No additional filtering needed for Chapter users
            pass

        elif office_loc == 'Dasmarinas':
            # Only Dasmariñas records
            query = query.filter(models.Records.origin == "Dasmariñas")
            print("🔍 Dasmarinas user - filtering to Dasmariñas records only")

        elif office_loc == 'Silang':
            # Only Silang records
            query = query.filter(models.Records.origin == "Silang")
            print("🔍 Silang user - filtering to Silang records only")

        # If office_loc is None or doesn't match known locations, return based only on status
        records = query.order_by(models.Records.record_id.desc()).all()
        print(f"✅ Found {len(records)} records for office location: {office_loc}")
        return records

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error fetching member records: {e}"
    
    
    
    
def archive_member_record(record_id):
    """Archive a member record by setting its status to 'archived'"""
    db_session = SessionLocal()
    try:
        record = db_session.query(models.Records).filter_by(record_id=record_id).first()
        if record:
            record.status = 'archived'
            db_session.commit()
            print(f"Record {record_id} archived successfully")
            return True
        else:
            print(f"Record {record_id} not found")
            return False
    except Exception as e:
        db_session.rollback()
        print(f"Error archiving record {record_id}: {e}")
        return False
    finally:
        db_session.close()


def get_unique_maab_numbers():
    db_session = SessionLocal()
    try:
        # Query distinct maab_no values
        maab_numbers = db_session.query(distinct(models.Entries.maab_no)).all()
        # flatten list of tuples to simple list
        return [m[0] for m in maab_numbers if m[0] is not None]
    except Exception as e:
        print(f"Error fetching MAAB numbers: {e}")
        return []
        
def get_claim_records():
    db_session = SessionLocal()
    try:
        # records = db_session.query(models.Claims).all()
        
        mc = models.Claims
        ec = models.Entries
        mr = models.Records
        mi = models.Members

        records = (
            db_session.query(
                mc,
                mr.effectivity_date,
                mi.first_name,
                mi.middle_name,
                mi.last_name,
                mi.suffix,
                mi.contact_no,
                mi.email,
            )
            .outerjoin(ec, mc.maab_no == ec.maab_no)
            .outerjoin(mr, ec.record_id == mr.record_id)
            .outerjoin(mi, ec.member_id == mi.member_id)
            .all()
        )
        
        results = []
        for mc_obj, effectivity_date, first_name, middle_name, last_name, suffix, contact_no, email in records:
            data = mc_obj.to_dict()
            data.update({
                "effectivity_date": effectivity_date.strftime("%Y-%m-%d") if effectivity_date else None,
                "first_name": first_name,
                "middle_name": middle_name,
                "last_name": last_name,
                "suffix": suffix,
                "contact_no": contact_no,
                "email": email,
            })
            results.append(data)
        
        return results
    except Exception as e:
        return "Error fetching claim records: {e}"
    
    '''
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
    '''

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

def get_new_claim_id():
    db_session = SessionLocal()
    try:
        claim_id = db_session.query(func.count(models.Claims.claim_id)).scalar()
        if claim_id is None:
            return 1
        else:
            return claim_id + 1
    except Exception as e:
        print(f"Error getting claim ID: {e}")
        return None

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
    db_session = SessionLocal()
    try:
        record = db_session.query(models.Records).filter_by(record_id=data['record_id']).first()
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
        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        print(f"Error saving record details: {e}")
        return False


# TODO add the new fields here to update
# TODO change the column 'status' to claim_status
# TODO change all instance of enhanced platinum to safe card
def save_claim_record(data):
    '''
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
    '''
    
    db_session = SessionLocal()
    try:
        claim_id = data.get('claim_id')
        
        if claim_id:
            # Try to get existing record
            claim = db_session.query(models.Claims).filter_by(claim_id=claim_id).first()
        else:
            claim = None

        if claim:
            # Update existing record
            model_columns = {col.name for col in models.Claims.__table__.columns}
            for field, value in data.items():
                if field in model_columns and field != "claim_id":
                    setattr(claim, field, value or None)
        else:
            # Create new record
            # Filter out keys that are not model columns
            model_columns = {col.name for col in models.Claims.__table__.columns}
            new_claim_data = {k: v or None for k, v in data.items() if k in model_columns}
            claim = models.Claims(**new_claim_data)
            db_session.add(claim)

        db_session.commit()
        return True

    except Exception as e:
        db_session.rollback()
        print(f"Error saving claim record: {e}")
        return False


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
    db_session = SessionLocal()
    try:
        # Join Entries and Members on member_id
        results = (
            db_session.query(
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
                models.Entries.tags,
                models.Entries.dispatch_ready,
                models.Entries.dispatch_id
            )
            .join(models.Members, models.Entries.member_id == models.Members.member_id)
            .filter(models.Entries.record_id == record_id)
            .all()
        )

        # Convert results to list of dicts
        col_names = [
            'entry_id', 'maab_category', 'maab_no', 'first_name', 'middle_name', 'last_name', 'suffix',
            'birth_date', 'age', 'sex', 'contact_no', 'email', 'address', 'blood_type', 'id_received',
            'declared', 'declaration_date', 'paid', 'OR_num', 'OR_date', 'remarks', 'tags', 'dispatch_ready',
            'dispatch_id'
        ]
        return [dict(zip(col_names, row)) for row in results]
    
    except Exception as e:
        return ["Error fetching entries: {e}"]

# WIP
def add_entry_content_online(fname, mname, lname, suffix, birthdate, age, sex, bloodtype, contact, email, municipality, address, maab_cat, origin):
    db_session = SessionLocal()
    try:
        #create new member first
        new_member = models.Members(
            first_name=fname,
            middle_name=mname,
            last_name=lname,
            suffix=suffix,
            birth_date=birthdate,
            age=age,
            sex=sex,
            contact_no=contact,
            email=email,
            address=address,
            blood_type=bloodtype,
        )
        
        db_session.add(new_member)
        db_session.commit()
        
        member_id = new_member.member_id
        
        # create new record first
        new_record = models.Records(
            year=datetime.now().year,
            id_received=None,
            declared=None,
            declaration_date=None,
            effectivity_date=date.today(), # set effectivity date to today, update when paid
            location_particular='Online Registration',
            location_category='Online', 
            municipality=municipality,
            district=tools.get_district_from_municipality(municipality),
            paid=None,
            origin=origin,
            remarks=None,
            tags=None
        )
        
        db_session.add(new_record)
        db_session.commit()
        
        record_id = new_record.record_id
        
        new_entry_content = models.Entries(
            record_id=record_id,
            maab_category=maab_cat,
            member_id=member_id
        )
        
        db_session.add(new_entry_content)
        db_session.commit()
        
        return True
    except Exception as e:
        db_session.rollback()
        print(f"Error adding entry content: {e}")
        return False


def save_entry_details(record_id, maab_category, maab_no, first_name, middle_name, last_name, suffix, birthdate, age, sex, bloodtype, contact, email, address, id_received, declared, declaration_date, paid, OR_num, OR_date, remarks, tags, dispatch_ready):
    db_session = SessionLocal()
    try:
        new_member_info = models.Members(
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            suffix=suffix,
            birth_date=birthdate,
            age=age,
            sex=sex,
            contact_no=contact,
            email=email,
            address=address,
            blood_type=bloodtype
        )
        db_session.add(new_member_info)
        db_session.commit()

        member_id = new_member_info.member_id
        
        new_entry_content = models.Entries(
            record_id=record_id,
            maab_category=maab_category,
            maab_no=maab_no,
            member_id=member_id,
            id_received=id_received,
            declared=declared,
            declaration_date=declaration_date,
            paid=paid,
            OR_num=OR_num,
            OR_date=OR_date,
            remarks=remarks,
            tags=tags,
            dispatch_ready=dispatch_ready
        )
        db_session.add(new_entry_content)
        db_session.commit()
        
        return True
    
    except Exception as e:
        db_session.rollback()
        print(f"Error adding entry content: {e}")
        return False

def transmit_dispatch_entries(dispatch_id, account_id=None):
    """
    Transmit all entries in a dispatch - KEEP DISPATCH ID VERSION
    """
    db_session = SessionLocal()
    try:
        print("=" * 60)
        print("🚀 TRANSMIT DISPATCH ENTRIES - KEEP DISPATCH ID VERSION")
        print(f"📦 Dispatch ID: {dispatch_id}")
        
        # 1️⃣ Get the dispatch
        dispatch = db_session.query(models.Dispatch).filter_by(dispatch_id=dispatch_id).first()
        if not dispatch:
            print(f"❌ Dispatch {dispatch_id} not found")
            return {"success": False, "error": "Dispatch not found"}
        
        print(f"✅ Found dispatch: {dispatch.dispatch_id}")
        
        # 2️⃣ Get all entries in this dispatch
        entries = db_session.query(models.Entries).filter_by(dispatch_id=dispatch_id).all()
        print(f"🔍 Found {len(entries)} entries in dispatch")
        
        if not entries:
            print("❌ No entries found in dispatch")
            return {"success": False, "error": "No entries found in dispatch"}
        
        transmitted_count = 0
        current_date = datetime.now().date()
        
        # Track unique record IDs to update records later
        record_ids_to_update = set()
        
        # 3️⃣ Process each entry - KEEP DISPATCH_ID, just update status
        for entry in entries:
            try:
                print(f"🔄 Processing entry {entry.entry_id}")
                
                # Mark entry as declared with current date BUT KEEP DISPATCH_ID
                entry.declared = True
                entry.declaration_date = current_date
                entry.tags = "Declared"
                # DON'T clear dispatch_id: entry.dispatch_id = None
                
                # Track the record ID for updating the record
                record_ids_to_update.add(entry.record_id)
                
                transmitted_count += 1
                print(f"✅ Successfully processed entry {entry.entry_id} (dispatch_id preserved)")
                
            except Exception as e:
                print(f"❌ Error processing entry {entry.entry_id}: {e}")
                continue
        
        # 4️⃣ Update all affected RECORDS - KEEP DISPATCH_ID
        print(f"📝 Updating {len(record_ids_to_update)} records...")
        for record_id in record_ids_to_update:
            try:
                record = db_session.query(models.Records).filter_by(record_id=record_id).first()
                if record:
                    # Update record status BUT KEEP DISPATCH_ID
                    record.declared = True
                    record.declaration_date = current_date
                    record.tags = "transmitted"
                    record.dispatch_ready = False  # No longer dispatch ready
                    # DON'T clear dispatch_id: record.dispatch_id = None
                    
                    print(f"✅ Updated record {record_id}: declared=True, tags=transmitted, dispatch_id preserved")
            except Exception as e:
                print(f"❌ Error updating record {record_id}: {e}")
                continue
        
        # 5️⃣ Update dispatch status
        print(f"📊 Updating dispatch status from '{dispatch.dispatch_status}' to 'dispatched'")
        
        dispatch.dispatch_status = 'dispatched'
        dispatch.date_dispatched = current_date
        dispatch.dispatch_total = transmitted_count
        
        print(f"✅ Dispatch updated: status=dispatched, date={current_date}, total={transmitted_count}")
        
        # 6️⃣ Commit changes
        db_session.commit()
        print("💾 Changes committed successfully")
        
        return {
            "success": True,
            "transmitted_count": transmitted_count,
            "dispatch_id": dispatch_id
        }
        
    except Exception as e:
        db_session.rollback()
        print(f"❌ Error transmitting dispatch: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db_session.close()
        print("🏁 TRANSMIT DISPATCH ENTRIES END")
        print("=" * 60)

def save_entry_update(data):
    db_session = SessionLocal()
    try:
        entry_id = data.get("entry_id")
        print(f"=== SAVE ENTRY UPDATES CALLED ===")
        print(f"Entry ID: {entry_id}")
        print(f"Full data received: {data}")
        
        if not entry_id:
            print("❌ No entry_id provided.")
            return False

        # Find the entry
        print(f"🔍 Looking for entry with ID: {entry_id}")
        entry = db_session.query(models.Entries).filter_by(entry_id=entry_id).first()
        if not entry:
            print(f"❌ Entry {entry_id} not found in database.")
            return False
        
        print(f"✅ Entry found: ID={entry.entry_id}, Member ID={entry.member_id}")

        # Update entry fields with proper validation
        update_fields = [
            'maab_category', 'maab_no', 'id_received', 'declared', 
            'paid', 'OR_num', 'remarks', 'tags', 'dispatch_ready'
        ]
        
        print("🔄 Updating entry fields...")
        for field in update_fields:
            if field in data:
                value = data[field]
                old_value = getattr(entry, field)
                print(f"   {field}: {old_value} -> {value}")
                
                # Handle boolean fields
                if field in ['id_received', 'declared', 'paid', 'dispatch_ready']:
                    if value in [True, 1, '1', 'true']:
                        value = True
                    elif value in [False, 0, '0', 'false', None]:
                        value = False
                    else:
                        value = bool(value)
                # Handle OR_num specifically
                elif field == 'OR_num':
                    if value and str(value).strip() != '':
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            value = str(value).strip()
                    else:
                        value = None
                # Handle other string fields
                elif field in ['maab_category', 'maab_no', 'remarks', 'tags']:
                    value = str(value) if value is not None else ""
                
                setattr(entry, field, value)

        # Handle dates with proper conversion
        print("🔄 Processing dates...")
        
        # Declaration date
        declaration_date = data.get("declaration_date")
        if declaration_date and str(declaration_date).strip():
            try:
                if isinstance(declaration_date, str):
                    entry.declaration_date = datetime.strptime(declaration_date, "%Y-%m-%d").date()
                print(f"   declaration_date set to: {entry.declaration_date}")
            except (ValueError, TypeError) as e:
                print(f"   ❌ Error parsing declaration_date '{declaration_date}': {e}")
                entry.declaration_date = None
        else:
            entry.declaration_date = None

        # OR date
        OR_date = data.get("OR_date")
        if OR_date and str(OR_date).strip():
            try:
                if isinstance(OR_date, str):
                    entry.OR_date = datetime.strptime(OR_date, "%Y-%m-%d").date()
                print(f"   OR_date set to: {entry.OR_date}")
            except (ValueError, TypeError) as e:
                print(f"   ❌ Error parsing OR_date '{OR_date}': {e}")
                entry.OR_date = None
        else:
            entry.OR_date = None

        # Find and update member information
        print(f"🔍 Looking for member with ID: {entry.member_id}")
        member = db_session.query(models.Members).filter_by(member_id=entry.member_id).first()
        if not member:
            print(f"❌ Member {entry.member_id} not found.")
            return False
        
        print(f"✅ Member found: ID={member.member_id}")

        # Update member fields with proper validation for ENUM fields
        member_fields = [
            'first_name', 'middle_name', 'last_name', 'suffix', 'age', 
            'sex', 'contact_no', 'email', 'address', 'blood_type'
        ]
        
        print("🔄 Updating member fields...")
        for field in member_fields:
            if field in data:
                value = data[field]
                old_value = getattr(member, field)
                print(f"   {field}: {old_value} -> {value}")
                
                # Handle specific field types
                if field == 'age' and value:
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        value = None
                # Handle sex field - convert empty string to NULL for ENUM
                elif field == 'sex':
                    if value == '' or value is None:
                        value = None  # Use NULL instead of empty string for ENUM
                    else:
                        value = str(value).strip()
                # Handle other string fields - convert empty string to None
                elif field in ['first_name', 'middle_name', 'last_name', 'suffix', 'contact_no', 'email', 'address', 'blood_type']:
                    if value == '':
                        value = None
                    else:
                        value = str(value) if value is not None else None
                
                setattr(member, field, value)

        # Handle birth date
        birth_date = data.get("birth_date")
        if birth_date and str(birth_date).strip():
            try:
                if isinstance(birth_date, str):
                    member.birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()
                print(f"   birth_date set to: {member.birth_date}")
            except (ValueError, TypeError) as e:
                print(f"   ❌ Error parsing birth_date '{birth_date}': {e}")
                member.birth_date = None
        else:
            member.birth_date = None

        # Commit all changes
        print("💾 Committing changes to database...")
        db_session.commit()
        print(f"✅ Successfully updated entry {entry_id} and member {member.member_id}")
        return True

    except Exception as e:
        db_session.rollback()
        print(f"❌ Error saving entry updates: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db_session.close()


def get_report_target_vs_actual(year):
    db_session = SessionLocal()
    try:
        categories = [
            "Classic", "Bronze", "Silver", "Gold", "Platinum", 
            "Enhanced Platinum", "Senior", "Senior+", "Safe Card"
        ]

        # DEBUG: Count total entries for the year
        total_entries = db_session.query(models.Entries).filter(
            extract("year", models.Entries.OR_date) == year
        ).count()
        print(f"🔍 DEBUG: Total entries in {year}: {total_entries}")

        # Query entries for monthly counts
        rows = (
            db_session.query(
                models.Entries.maab_category.label("category"),
                extract("month", models.Entries.OR_date).label("month"),
                func.count(models.Entries.entry_id).label("count")
            )
            .filter(
                extract("year", models.Entries.OR_date) == year,
                models.Entries.maab_category.in_(categories)
            )
            .group_by(
                models.Entries.maab_category,
                extract("month", models.Entries.OR_date)
            )
            .all()
        )

        print(f"🔍 DEBUG: Grouped entries found: {len(rows)}")
        for category, month, count in rows:
            print(f"  - {category}, Month {month}: {count}")

        # DEBUG: Check for entries with NULL or different categories
        null_category_entries = db_session.query(models.Entries).filter(
            extract("year", models.Entries.OR_date) == year,
            ~models.Entries.maab_category.in_(categories)
        ).count()
        print(f"🔍 DEBUG: Entries with non-matching categories: {null_category_entries}")

        # DEBUG: Check for entries with NULL OR_date
        null_date_entries = db_session.query(models.Entries).filter(
            models.Entries.OR_date.is_(None)
        ).count()
        print(f"🔍 DEBUG: Entries with NULL OR_date: {null_date_entries}")

        target_row = db_session.query(models.Report_TvA).filter(models.Report_TvA.year == year).first()

        category_to_column = {
            "Classic": "classic",
            "Bronze": "bronze", 
            "Silver": "silver",
            "Gold": "gold",
            "Platinum": "platinum",
            "Enhanced Platinum": "safe_card",
            "Senior": "senior",
            "Senior+": "senior_plus",
            "Safe Card": "safe_card"
        }
        
        output = {}
        for cat in categories:
            target_col = category_to_column.get(cat)
            target_value = getattr(target_row, target_col, 0) if target_row else 0
            output[cat] = {0: target_value, **{m: 0 for m in range(1, 13)}}

        # Fill monthly counts from entries
        for category, month, count in rows:
            month = int(month)
            if category in output:
                output[category][month] = count

        # DEBUG: Calculate total detected vs expected
        total_detected = sum(sum(cat_data.values()) for cat_data in output.values()) - sum(cat_data[0] for cat_data in output.values())
        print(f"🔍 DEBUG: Total detected in report: {total_detected}")
        print(f"🔍 DEBUG: Missing entries: {total_entries - total_detected}")

        return output
    except Exception as e:
        print(f"Error fetching report data: {e}")
        return {}
    finally:
        db_session.close()

def auto_create_yearly_targets():
    """Automatically create target rows for new year on January 1st"""
    try:
        from datetime import datetime
        current_date = datetime.now()
        current_year = current_date.year
        
        db_session = SessionLocal()
        
        # Check if target already exists for this year
        existing_target = db_session.query(models.Report_TvA).filter(
            models.Report_TvA.year == current_year
        ).first()
        
        if not existing_target:
            # Create new target row with null/zero values
            new_target = models.Report_TvA(
                year=current_year,
                classic=0,
                bronze=0,
                silver=0,
                gold=0,
                platinum=0,
                safe_card=0,
                senior=0,
                senior_plus=0
            )
            db_session.add(new_target)
            db_session.commit()
            print(f"✅ Auto-created target row for year {current_year}")
            return True
        else:
            print(f"✅ Target row for year {current_year} already exists")
            return False
            
    except Exception as e:
        print(f"❌ Error auto-creating yearly targets: {e}")
        return False
    finally:
        db_session.close()

def get_current_active_dispatch(db_session=None):
    """Get current active dispatch with optional session parameter"""
    if db_session is None:
        db_session = SessionLocal()
        close_session = True
    else:
        close_session = False
        
    try:
        last_dispatch = (
            db_session.query(models.Dispatch)
            .filter(models.Dispatch.dispatch_status == 'current')
            .order_by(models.Dispatch.dispatch_id.desc())
            .first()
        )
        print('db_conn - current active dispatch', last_dispatch.dispatch_id if last_dispatch else None)
        return last_dispatch
    except Exception as e:
        print(f"Error fetching current active dispatch: {e}")
        return None
    finally:
        if close_session:
            db_session.close()

def add_to_dispatch(record_ids=None):
    db_session = SessionLocal()
    try:
        print("=" * 60)
        print("🚀 DEBUG: add_to_dispatch START - RECORD LEVEL CHECK")
        print(f"📦 Input record_ids: {record_ids}")
        
        # 1️⃣ Get current active dispatch
        current_dispatch = get_current_active_dispatch()
        if not current_dispatch:
            print("❌ No active dispatch found")
            return 0

        print(f"✅ Active dispatch: ID={current_dispatch.dispatch_id}, Status={current_dispatch.dispatch_status}")

        # 2️⃣ Check record-level status first
        added_count = 0
        for record_id in record_ids:
            print(f"\n--- Checking record_id: {record_id} ---")
            
            # Get the RECORD to check its status
            record = db_session.query(models.Records).filter(
                models.Records.record_id == record_id
            ).first()
            
            if not record:
                print(f"   ❌ Record {record_id} not found")
                continue
                
            print(f"   📋 Record {record_id}: dispatch_ready={record.dispatch_ready}, declared={record.declared}")
            
            # Check RECORD-LEVEL eligibility
            is_record_eligible = (
                record.dispatch_ready == True and 
                record.declared == False
            )
            
            print(f"   ✅ Record eligible? {is_record_eligible}")
            
            if not is_record_eligible:
                print(f"   ❌ Record {record_id} not eligible at record level")
                continue
            
            # 3️⃣ Get all entries for this eligible record
            entries = db_session.query(models.Entries).filter(
                models.Entries.record_id == record_id
            ).all()
            
            print(f"   📦 Found {len(entries)} entries for record {record_id}")
            
            # 4️⃣ Add ALL entries from this eligible record to dispatch
            for entry in entries:
                # Only check if entry is not already in THIS dispatch
                if entry.dispatch_id != current_dispatch.dispatch_id:
                    print(f"     🎯 ADDING entry {entry.entry_id} to dispatch {current_dispatch.dispatch_id}")
                    entry.dispatch_id = current_dispatch.dispatch_id
                    added_count += 1
                else:
                    print(f"     ℹ️  Entry {entry.entry_id} already in dispatch")
            
            # 🔥 CRITICAL FIX: Update the RECORD's dispatch_id too
            print(f"     📝 UPDATING record {record_id} dispatch_id to {current_dispatch.dispatch_id}")
            record.dispatch_id = current_dispatch.dispatch_id

        # 5️⃣ Commit changes
        print(f"\n💾 Committing {added_count} changes...")
        db_session.commit()
        print(f"✅ Successfully added {added_count} entries to dispatch and updated record dispatch_ids")

        return added_count

    except Exception as e:
        db_session.rollback()
        print(f"❌ Error in add_to_dispatch: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        db_session.close()
        print("🏁 DEBUG: add_to_dispatch END")
        print("=" * 60)

def add_to_dispatch(record_ids=None):
    db_session = SessionLocal()
    try:
        print("=" * 60)
        print("🚀 DEBUG: add_to_dispatch START - RECORD LEVEL CHECK")
        print(f"📦 Input record_ids: {record_ids}")
        
        # 1️⃣ Get current active dispatch
        current_dispatch = get_current_active_dispatch()
        if not current_dispatch:
            print("❌ No active dispatch found")
            return 0

        print(f"✅ Active dispatch: ID={current_dispatch.dispatch_id}, Status={current_dispatch.dispatch_status}")

        # 2️⃣ Check record-level status first
        added_count = 0
        for record_id in record_ids:
            print(f"\n--- Checking record_id: {record_id} ---")
            
            # Get the RECORD to check its status
            record = db_session.query(models.Records).filter(
                models.Records.record_id == record_id
            ).first()
            
            if not record:
                print(f"   ❌ Record {record_id} not found")
                continue
                
            print(f"   📋 Record {record_id}: dispatch_ready={record.dispatch_ready}, declared={record.declared}")
            
            # Check RECORD-LEVEL eligibility
            is_record_eligible = (
                record.dispatch_ready == True and 
                record.declared == False
            )
            
            print(f"   ✅ Record eligible? {is_record_eligible}")
            
            if not is_record_eligible:
                print(f"   ❌ Record {record_id} not eligible at record level")
                continue
            
            # 3️⃣ Get all entries for this eligible record
            entries = db_session.query(models.Entries).filter(
                models.Entries.record_id == record_id
            ).all()
            
            print(f"   📦 Found {len(entries)} entries for record {record_id}")
            
            # 4️⃣ Add ALL entries from this eligible record to dispatch
            for entry in entries:
                # Only check if entry is not already in THIS dispatch
                if entry.dispatch_id != current_dispatch.dispatch_id:
                    print(f"     🎯 ADDING entry {entry.entry_id} to dispatch {current_dispatch.dispatch_id}")
                    entry.dispatch_id = current_dispatch.dispatch_id
                    added_count += 1
                else:
                    print(f"     ℹ️  Entry {entry.entry_id} already in dispatch")
            
            # 🔥 CRITICAL FIX: Update the RECORD's dispatch_id too
            print(f"     📝 UPDATING record {record_id} dispatch_id to {current_dispatch.dispatch_id}")
            record.dispatch_id = current_dispatch.dispatch_id

        # 5️⃣ Commit changes
        print(f"\n💾 Committing {added_count} changes...")
        db_session.commit()
        print(f"✅ Successfully added {added_count} entries to dispatch and updated record dispatch_ids")

        return added_count

    except Exception as e:
        db_session.rollback()
        print(f"❌ Error in add_to_dispatch: {e}")
        import traceback
        traceback.print_exc()
        return 0
    finally:
        db_session.close()
        print("🏁 DEBUG: add_to_dispatch END")
        print("=" * 60)

def remove_entries_from_dispatch(selected_rows):
    """
    Remove selected entries from dispatch by setting their dispatch_id to NULL
    """
    db_session = SessionLocal()
    try:
        print("=" * 60)
        print("🚀 DEBUG: remove_entries_from_dispatch START")
        print(f"📦 Selected rows: {len(selected_rows)}")
        
        if not selected_rows:
            return {"success": False, "error": "No entries provided"}
        
        removed_count = 0
        processed_entry_ids = []
        
        # Process each selected entry
        for row in selected_rows:
            try:
                entry_id = row.get('entry_id')
                if not entry_id:
                    print(f"❌ No entry_id in row: {row}")
                    continue
                
                print(f"🔄 Removing entry {entry_id} from dispatch")
                
                # Find the entry
                entry = db_session.query(models.Entries).filter_by(entry_id=entry_id).first()
                if not entry:
                    print(f"❌ Entry {entry_id} not found")
                    continue
                
                # Store the record_id before clearing (for record update)
                record_id = entry.record_id
                
                # Remove from dispatch by setting dispatch_id to NULL
                entry.dispatch_id = None
                processed_entry_ids.append(entry_id)
                removed_count += 1
                
                print(f"✅ Entry {entry_id} removed from dispatch")
                
                # Check if this was the last entry in the record for this dispatch
                # If so, clear the record's dispatch_id too
                other_entries_in_dispatch = db_session.query(models.Entries).filter(
                    models.Entries.record_id == record_id,
                    models.Entries.dispatch_id.isnot(None)
                ).count()
                
                if other_entries_in_dispatch == 0:
                    # No more entries in this record are in dispatch, clear record dispatch_id
                    record = db_session.query(models.Records).filter_by(record_id=record_id).first()
                    if record:
                        print(f"📝 Clearing dispatch_id from record {record_id} (no more entries in dispatch)")
                        record.dispatch_id = None
                
            except Exception as e:
                print(f"❌ Error processing entry {row.get('entry_id')}: {e}")
                continue
        
        # Commit all changes
        db_session.commit()
        print(f"💾 Successfully removed {removed_count} entries from dispatch")
        
        return {
            "success": True,
            "removed_count": removed_count,
            "processed_entry_ids": processed_entry_ids
        }
        
    except Exception as e:
        db_session.rollback()
        print(f"❌ Error removing from dispatch: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        db_session.close()
        print("🏁 DEBUG: remove_entries_from_dispatch END")
        print("=" * 60)

def get_current_dispatch_contents(dispatch_id):
    db_session = SessionLocal()
    try:
        if not dispatch_id:
            print("No dispatch_id provided")
            return []
            
        print(f"🔍 Fetching dispatch contents for dispatch_id: {dispatch_id}")
        
        current_dispatch_contents = (
            db_session.query(
                models.Entries.entry_id,
                models.Entries.record_id,
                models.Entries.maab_category,
                models.Entries.maab_no,
                models.Entries.member_id,
                models.Members.first_name,
                models.Members.middle_name,
                models.Members.last_name,
                models.Members.suffix,
                models.Members.birth_date,
                models.Records.effectivity_date,
                models.Records.location_particular
            )
            .join(models.Members, models.Entries.member_id == models.Members.member_id)
            .join(models.Records, models.Entries.record_id == models.Records.record_id)
            .filter(models.Entries.dispatch_id == dispatch_id)
            .all()
        )
        
        print(f'✅ Found {len(current_dispatch_contents)} entries in dispatch {dispatch_id}')
        return current_dispatch_contents
        
    except Exception as e:
        print(f"❌ Error fetching current dispatch contents: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        db_session.close()

def get_all_dispatch_records():
    db_session = SessionLocal()
    try:
        dispatch_records = (
            db_session.query(models.Dispatch)
            .order_by(models.Dispatch.dispatch_id.desc())
            .all()
        )
        return dispatch_records
    except Exception as e:
        print(f"Error fetching dispatch records: {e}")
        return []   

def POST_action_log(current_user=None, current_user_lvl=None, action=None, desc=None, current_user_id=None):
    """ for logging actions on audit_trails table """
    
    db_session = SessionLocal()
    
    try:
        # Get user info from current_user if available
        if current_user_id and not current_user:
            user = db_session.query(models.Accounts).filter_by(account_id=current_user_id).first()
            if user:
                current_user = f"{user.first_name} {user.last_name}"
                current_user_lvl = user.user_level
        
        audit_log = models.Logs(
            date=datetime.now(),
            staff_name=current_user or "System",
            user_level=current_user_lvl or "Unknown",
            action_name=action or "Unknown Action",
            description=desc or "No description",
            account_id=current_user_id
        )
        
        db_session.add(audit_log)
        db_session.commit()
        print(f"✅ Action logged: {action} - {desc}")
        return True
    except Exception as e:
        db_session.rollback()
        print(f"❌ Error logging action: {e}")
        return False
    finally:
        db_session.close()


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

def add_inventory_ids(category, prefix, start_num, count, username=None, user_level=None, account_id=None):
    """Add multiple IDs to inventory with sequential numbers"""
    db_session = SessionLocal()
    
    try:
        added_count = 0
        duplicate_count = 0
        error_count = 0
        added_ids = []
        duplicate_ids = []
        
        # Pre-check for existing IDs in the range
        end_num = start_num + count - 1
        existing_ids = db_session.query(models.Inventory.maab_no).filter(
            models.Inventory.maab_no.between(
                f"{prefix}{start_num:07d}", 
                f"{prefix}{end_num:07d}"
            )
        ).all()
        
        existing_set = {id[0] for id in existing_ids}
        
        if existing_set:
            duplicate_count = len(existing_set)
            duplicate_ids = sorted(list(existing_set))
            print(f"Found {duplicate_count} existing IDs in the range")
        
        # Generate and add new IDs
        for i in range(count):
            current_num = start_num + i
            maab_no = f"{prefix}{current_num:07d}"
            
            # Skip if already exists
            if maab_no in existing_set:
                continue
            
            try:
                # Create new inventory entry
                new_id = models.Inventory(
                    maab_category=category,
                    maab_no=maab_no,
                    used=False,
                    allocated_to=None,
                    remarks=f"Added in batch - {datetime.now().strftime('%Y-%m-%d')}"
                )
                
                db_session.add(new_id)
                added_ids.append(maab_no)
                added_count += 1
                
            except Exception as e:
                print(f"Error adding ID {maab_no}: {e}")
                error_count += 1
        
        db_session.commit()
        
        # Log the action if user info is provided
        if username and user_level and account_id:
            POST_action_log(
                username,
                user_level,
                'Add Inventory Stock',
                f'Added {added_count} IDs for {category} (Range: {prefix}{start_num:07d}-{prefix}{end_num:07d}). '
                f'Duplicates: {duplicate_count}, Errors: {error_count}',
                account_id
            )
        
        return {
            "success": True,
            "added_count": added_count,
            "duplicate_count": duplicate_count,
            "error_count": error_count,
            "added_ids": added_ids,
            "duplicate_ids": duplicate_ids
        }
        
    except Exception as e:
        db_session.rollback()
        print(f"Error adding inventory IDs: {e}")
        return {
            "success": False,
            "error": str(e),
            "added_count": 0,
            "duplicate_count": 0,
            "error_count": count
        }
    finally:
        db_session.close()

def check_user_exists(email):
    """
    Check if email exists in accounts table
    """
    try:
        db_session = SessionLocal()
        # FIXED: Using the correct table name and column names
        user = db_session.query(models.Accounts).filter(
            models.Accounts.email == email,
            models.Accounts.acct_status.in_(["approved", "pending"])
        ).first()
        
        exists = user is not None
        print(f"🔍 DEBUG check_user_exists: email='{email}', exists={exists}")
        return exists
        
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return False
    finally:
        db_session.close()

def check_user_authorized(email):
    """
    Check if user is authorized for OTP (staff or specific roles)
    """
    try:
        db_session = SessionLocal()
        # FIXED: Using the correct table name and column names
        user = db_session.query(models.Accounts).filter(
            models.Accounts.email == email,
            models.Accounts.acct_status.in_(["approved", "pending"])
        ).first()
        
        if user:
            # Define which roles are allowed to use OTP
            allowed_roles = ['staff', 'admin', 'superadmin']  # Adjust as needed
            authorized = user.user_level in allowed_roles
            print(f"🔍 DEBUG check_user_authorized: email='{email}', user_level='{user.user_level}', authorized={authorized}")
            return authorized
        
        print(f"🔍 DEBUG check_user_authorized: User not found for email '{email}'")
        return False
        
    except Exception as e:
        print(f"Error checking user authorization: {e}")
        return False
    finally:
        db_session.close()

def GET_audit_logs():
    db_session = SessionLocal()
    try:
        logs = db_session.query(models.Logs).order_by(models.Logs.date.desc()).all()
        return logs
    except Exception as e:
        print(f"Error fetching audit logs: {e}")
        return []

def save_profile_pic(account_id, image_data):
    """Save profile picture (BLOB) to the database."""
    db_session = SessionLocal()
    try:
        user = db_session.query(models.Accounts).filter_by(account_id=account_id).first()
        if user:
            user.profile_pic = image_data
            db_session.commit()
            print(f"✅ Profile picture updated for user {account_id}")
            return True
        print(f"❌ User {account_id} not found.")
        return False
    except Exception as e:
        db_session.rollback()
        print(f"Error saving profile picture: {e}")
        return False


def get_profile_pic(account_id):
    """Retrieve the profile picture BLOB from the database."""
    db_session = SessionLocal()
    try:
        user = db_session.query(models.Accounts).filter_by(account_id=account_id).first()
        return user.profile_pic if user and user.profile_pic else None
    except Exception as e:
        print(f"Error fetching profile picture: {e}")
        return None


def update_user_details(account_id, first_name, middle_name, last_name, birth_date, contact_no, email):
    # Find the user by their account_id
    session = SessionLocal()  # create a session instance
    user = session.query(models.Accounts).filter(models.Accounts.account_id == account_id).first()

    # If user is found, update the fields
    if user:
        user.first_name = first_name
        user.middle_name = middle_name
        user.last_name = last_name
        user.birth_date = birth_date
        user.contact_no = contact_no
        user.email = email

        try:
            # Commit the changes to the database
            session.commit()
            print(f"User {account_id} details updated successfully.")
            return True
        except Exception as e:
            # If there is an error, roll back the changes
            session.rollback()
            print(f"Error updating user details: {e}")
            return False
    else:
        print(f"User with account_id {account_id} not found.")
        return False


def archive_member_record_with_log(record_id, account_id):
    """Archive a member record and log the action in the same session"""
    db_session = SessionLocal()
    try:
        # Archive the record
        record = db_session.query(models.Records).filter_by(record_id=record_id).first()
        if not record:
            print(f"Record {record_id} not found")
            return False
        
        record.status = 'archived'
        
        # Get user details for logging (using the same session)
        user = db_session.query(models.Accounts).filter_by(account_id=account_id).first()
        if user:
            # Log the action
            audit_log = models.Logs(
                date=datetime.now(),
                staff_name=user.username,
                user_level=user.user_level,
                action_name='Archive Record',
                description=f'Archived record ID: {record_id}',
                account_id=account_id
            )
            db_session.add(audit_log)
        
        db_session.commit()
        print(f"Record {record_id} archived successfully with logging")
        return True
        
    except Exception as e:
        db_session.rollback()
        print(f"Error archiving record {record_id}: {e}")
        return False
    finally:
        db_session.close()
    
    '''
    now = datetime.now()
    current_date_time = now.strftime('%Y-%m-%d %H:%M:%S')

    
    
    with conn.cursor() as cursor:
        cursor.execute('INSERT INTO audit_trails VALUES (%s, %s, %s, %s, %s, %s)',
                       (None, current_date_time, current_user, current_user_lvl, action, desc))
        conn.commit()
    '''

if __name__ == '__main__':
    print('do no run this module directly lol')
    print('use initialize_database.py')
    
    
