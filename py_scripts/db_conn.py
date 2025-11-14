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

if os.getenv('FLASK_ENV') == 'production':
    DB_CONNECTION_MODE = os.getenv('DB_CONNECTION_MODE', 'aiven').lower()
else:
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent
    env_loc = parent_dir/'creds.env'

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


def sign_in(username=None, password=None):    
    db_session = SessionLocal()

    user = db_session.query(models.Accounts).filter(
        models.Accounts.username == username,
        models.Accounts.acct_status.in_(["approved", "pending"])
    ).first()

    if user and tools.check_password(password, user.password):
        return user  # return full user object instead of "success/pending/fail"
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
            acct_status='pending',  # default status
            acct_review_date=None  # default review date
        )
        db_session.add(new_account)
        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        print(f"Error creating account: {e}")
        return str(e)
    
    
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
def send_otp_email(email, otp):
    """Send OTP to the user's email."""
    subject = "Your OTP Code"
    body = f"Your OTP code for FGMS is: {otp}. This will expire in 5 minutes."

    # TODO change the from with name of the organization
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
    """Update the password in the database."""
    conn = conn_init()
    Session = sessionmaker(bind=conn)

    salted_pass = tools.hash_password(new_password)

    with Session() as session:
        query = text("UPDATE accounts SET password = :new_password WHERE email = :email")
        session.execute(query, {"new_password": salted_pass, "email": email})
        session.commit()

# ? RESET PASS END    
    


def create_dispatch(dispatch_type, origin, year, cutoff, late, remarks):
    db_session = SessionLocal()
    try:
        new_dispatch = models.Dispatch(
            dispatch_type=dispatch_type,
            dispatch_origin=origin,
            dispatch_year=year,
            dispatch_cutoff=cutoff,
            late_declare=late,
            dispatch_remarks=remarks
        )
        db_session.add(new_dispatch)
        db_session.commit()
        return True
    except Exception as e:
        db_session.rollback()
        print(f"Error creating dispatch: {e}")
        return str(e)









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
            print(f"Resetting password for account ID {id}")
            initials = (account.first_name[:1] + account.middle_name[:1] + account.last_name[:1]).lower().strip()
            bdate = str(account.birth_date).replace('-', '') if account.birth_date else '00000000'
            
            account.password = tools.hash_password(bdate + initials)
            
            db_session.commit()
            return True
        return False
    except Exception as e:
        db_session.rollback()
        print(f"Error approving account: {e}")
        return False


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



def get_member_records():
    db_session = SessionLocal()
    try:
        records = db_session.query(models.Records).order_by(models.Records.record_id.desc()).all()
        return records
    except Exception as e:
        return "Error fetching member records: {e}"
    '''
        query = text("SELECT * FROM membership_records")
        result = conn.execute(query)
        records = result.fetchall()
        return records
    '''

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


def save_entry_updates(data):
    db_session = SessionLocal()
    try:
        entry_id = data.get("entry_id")
        if not entry_id:
            print("No entry_id provided.")
            return None

        # =======================
        # UPDATE ENTRY
        # =======================
        entry = db_session.query(models.Entries).filter_by(entry_id=entry_id).first()
        if not entry:
            print("Entry not found.")
            return None

        entry.maab_category = data["maab_category"]
        entry.maab_no = data["maab_no"]
        entry.id_received = data["id_received"]
        entry.declared = data["declared"]
        entry.paid = data["paid"]
        entry.OR_num = data["OR_num"]
        entry.remarks = data["remarks"]
        entry.tags = data["tags"]
        entry.dispatch_ready = data["dispatch_ready"]
        entry.dispatch_id = data["dispatch_id"]

        entry.declaration_date = (
            datetime.strptime(data["declaration_date"], "%m/%d/%Y").date()
            if data["declaration_date"] else None
        )

        entry.OR_date = (
            datetime.strptime(data["OR_date"], "%m/%d/%Y").date()
            if data["OR_date"] else None
        )

        # =======================
        # UPDATE MEMBER INFO
        # =======================
        member = db_session.query(models.Members).filter_by(member_id=entry.member_id).first()
        if not member:
            print("Member not found.")
            return None

        member.first_name = data["first_name"]
        member.middle_name = data["middle_name"]
        member.last_name = data["last_name"]
        member.suffix = data["suffix"]
        member.birth_date = (
            datetime.strptime(data["birth_date"], "%m/%d/%Y").date()
            if data["birth_date"] else None
        )
        member.age = data["age"]
        member.sex = data["sex"]
        member.contact_no = data["contact_no"]
        member.email = data["email"]
        member.address = data["address"]
        member.blood_type = data["blood_type"]

        # =======================
        # SAVE ALL CHANGES
        # =======================
        db_session.commit()

        return True

    
    except Exception as e:
        db_session.rollback()
        print(f"Error saving entry updates: {e}")
        return False




def get_current_active_dispatch():
    db_session = SessionLocal()
    try:

        last_dispatch = (
            db_session.query(models.Dispatch)
            .filter(models.Dispatch.dispatch_status == 'current')
            .order_by(models.Dispatch.dispatch_id.desc())  # or .order_by(models.Dispatch.created_at.desc())
            .first()
        )
        print('db_conn - current active dispatch', last_dispatch.dispatch_id)
        return last_dispatch
    except Exception as e:
        print(f"Error fetching current active dispatch: {e}")
        return None

def add_to_dispatch():
    db_session = SessionLocal()
    try:
        # 1️⃣ Get current active dispatch
        current_dispatch = get_current_active_dispatch()
        if not current_dispatch:
            print("No active dispatch found.")
            return None

        # 2️⃣ Get all eligible entries
        entries_to_dispatch = (
            db_session.query(models.Entries)
            .filter(
                (models.Entries.dispatch_ready.is_(True)) &
                ((models.Entries.declared.is_(False)) | (models.Entries.declared.is_(None))) &
                ((models.Entries.dispatch_id.is_(None)) | (models.Entries.dispatch_id == 0))
            )
            .all()
        )

        if not entries_to_dispatch:
            print("No entries found for dispatch.")
            return None

        # 3️⃣ Assign each entry to the current active dispatch
        for entry in entries_to_dispatch:
            entry.dispatch_id = current_dispatch.dispatch_id

        # 4️⃣ Commit all changes
        db_session.commit()
        print(f"Assigned {len(entries_to_dispatch)} entries to dispatch {current_dispatch.dispatch_id}")

        return len(entries_to_dispatch)

    except Exception as e:
        db_session.rollback()
        print(f"Error assigning entries to active dispatch: {e}")
        return None

def get_current_dispatch_contents(dispatch_id):
    db_session = SessionLocal()
    try:
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
        print('db_conn - current dispatch contents', current_dispatch_contents)
        return current_dispatch_contents
    except Exception as e:
        print(f"Error fetching current dispatch contents: {e}")
        return None

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


def POST_action_log(current_user=None, current_user_lvl=None, action=None, desc=None, current_user_id=None):
    """ for logging actions on audit_trails table """
    
    db_session = SessionLocal()
    
    try:
        audit_log = models.Logs(
            date=datetime.now(),
            staff_name=current_user,
            user_level=current_user_lvl,
            action_name=action,
            description=desc,
            account_id=current_user_id
        )
        print(audit_log)
        
        db_session.add(audit_log)
        db_session.commit()
        print("Action logged successfully.")
    except Exception as e:
        db_session.rollback()
        print(f"Error logging action: {e}")    
    
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
    
    