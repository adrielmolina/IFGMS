from sqlalchemy import Column, Integer, String, Date, DECIMAL, Boolean, Text, ForeignKey, Enum, SmallInteger
from sqlalchemy.ext.declarative import declarative_base
from flask_login import UserMixin

Base = declarative_base()


class Accounts(Base, UserMixin):
    __tablename__ = 'accounts'

    account_id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255))
    first_name = Column(String(255))
    middle_name = Column(String(255))
    last_name = Column(String(255))
    contact_no = Column(String(255))
    acct_created = Column(Date)
    office_location = Column(String(255))
    user_level = Column(String(255))
    acct_status = Column(String(255))
    acct_review_date = Column(Date)
    birth_date = Column(Date)
    password = Column(String(255))

    def get_id(self):
        # (default is id, so override it for account_id)
        return str(self.account_id)


class Records(Base):
    __tablename__ = 'membership_records'

    record_id = Column(Integer, primary_key=True)
    year = Column(Integer)
    id_received = Column(Boolean)
    declared = Column(Boolean)
    declaration_date = Column(Date)
    effectivity_date = Column(Date)
    location_particular = Column(String(255))
    location_category = Column(String(255))
    municipality = Column(String(255))
    district = Column(String(255))
    paid = Column(Boolean)
    origin = Column(String(255))
    remarks = Column(Text)
    tags = Column(String(255))


class Entries(Base):
    __tablename__ = 'entry_contents'

    entry_id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey('membership_records.record_id'))
    maab_category = Column(String(255))
    maab_no = Column(String(255))
    member_id = Column(Integer, ForeignKey('members_info.member_id'))
    id_received = Column(Boolean)
    declared = Column(Boolean)
    declaration_date = Column(Date)
    paid = Column(Boolean)
    OR_num = Column(Integer)
    OR_date = Column(Date)
    remarks = Column(Text)
    tags = Column(String(255))


class Members(Base):
    __tablename__ = 'members_info'

    member_id = Column(Integer, primary_key=True)
    first_name = Column(String(255))
    middle_name = Column(String(255))
    last_name = Column(String(255))
    suffix = Column(String(255))
    birth_date = Column(Date)
    age = Column(Integer)
    sex = Column(String(255))
    contact_no = Column(String(255))
    email = Column(String(255))
    address = Column(String(255))
    blood_type = Column(String(255))


class Inventory(Base):
    __tablename__ = 'inventory'
    
    inv_id = Column(Integer, primary_key=True)
    maab_category = Column(Enum(
        'Classic', 'Bronze', 'Silver', 'Gold', 'Platinum', 
        'Enhanced Platinum', 'Senior', 'Senior+'))
    maab_no = Column(String(255))
    used = Column(SmallInteger)
    remarks = Column(Text)
    allocated_to = Column(Enum('Chapter', 'Dasmarinas', 'Silang'))
    

class Claims(Base):
    __tablename__ = 'maab_claims'

    claim_id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    date_filed = Column(Date)
    received_by = Column(String(255))
    claim_origin = Column(String(255))
    date_of_loss = Column(Date)
    maab_no = Column(String(255), ForeignKey('entry_contents.maab_no'))
    same_as_insured = Column(Boolean)
    claimant_first_name = Column(String(255))
    claimant_middle_name = Column(String(255))
    claimant_last_name = Column(String(255))
    claimant_suffix = Column(String(255))
    relation_to_insured = Column(String(255), default='SAME')
    claimant_contact_no = Column(String(255))
    claimant_email = Column(String(255))
    claim_remarks = Column(Text)
    status = Column(String(255))
    date_released = Column(Date)
    chinabank_check_no = Column(Integer)
    chinabank_amount = Column(DECIMAL(10, 0))
    bpi_check_no = Column(Integer)
    bpi_amount = Column(DECIMAL(10, 0))
    release_remarks = Column(Text)
    scanned_docs = Column(String(255))  # GDrive folder for claim docs
    prm_file = Column(String(255))      # Link to prm file
    quit_claim_file = Column(String(255))  # Link to quit claim file
    picked_up = Column(Boolean)
    date_picked_up = Column(Date)
    req_claim_form = Column(Boolean)
    req_prc_id = Column(Boolean)
    req_med_cert = Column(Boolean)
    req_hos_bill_or = Column(Boolean)
    req_state_of_acc = Column(Boolean)
    req_doctor_pres = Column(Boolean)
    req_purchased_meds = Column(Boolean)
    req_med_records = Column(Boolean)
    req_animal_bite_treat_rec = Column(Boolean)
    req_incident_rep = Column(Boolean)
    req_police_rep = Column(Boolean)
    req_brgy_rep = Column(Boolean)
    req_drivers_lic = Column(Boolean)
    req_birth_cert = Column(Boolean)
    req_marriage_cert = Column(Boolean)
    req_death_cert = Column(Boolean)
    req_burial_receipts = Column(Boolean)
    sent_advanced_notice = Column(Boolean)
    claim_type = Column(Enum('ACCIDENT', 'DEATH'))
    

class Claims_Archive(Base):
    __tablename__ = 'maab_claims_archive'

    archived_claim_id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    claim_id = Column(Integer, unique=True, nullable=False)
    date_filed = Column(Date)
    received_by = Column(String(255))
    claim_origin = Column(String(255))
    date_of_loss = Column(Date)
    maab_no = Column(String(255), ForeignKey('entry_contents.maab_no'))
    same_as_insured = Column(Boolean)
    claimant_first_name = Column(String(255))
    claimant_middle_name = Column(String(255))
    claimant_last_name = Column(String(255))
    claimant_suffix = Column(String(255))
    relation_to_insured = Column(String(255), default='SAME')
    claimant_contact_no = Column(String(255))
    claimant_email = Column(String(255))
    claim_remarks = Column(Text)
    status = Column(String(255))
    date_released = Column(Date)
    chinabank_check_no = Column(Integer)
    chinabank_amount = Column(DECIMAL(10, 0))
    bpi_check_no = Column(Integer)
    bpi_amount = Column(DECIMAL(10, 0))
    release_remarks = Column(Text)
    scanned_docs = Column(String(255))  # GDrive folder for claim docs
    prm_file = Column(String(255))      # Link to prm file
    quit_claim_file = Column(String(255))  # Link to quit claim file
    picked_up = Column(Boolean)
    date_picked_up = Column(Date)
    req_claim_form = Column(Boolean)
    req_prc_id = Column(Boolean)
    req_med_cert = Column(Boolean)
    req_hos_bill_or = Column(Boolean)
    req_state_of_acc = Column(Boolean)
    req_doctor_pres = Column(Boolean)
    req_purchased_meds = Column(Boolean)
    req_med_records = Column(Boolean)
    req_animal_bite_treat_rec = Column(Boolean)
    req_incident_rep = Column(Boolean)
    req_police_rep = Column(Boolean)
    req_brgy_rep = Column(Boolean)
    req_drivers_lic = Column(Boolean)
    req_birth_cert = Column(Boolean)
    req_marriage_cert = Column(Boolean)
    req_death_cert = Column(Boolean)
    req_burial_receipts = Column(Boolean)
    sent_advanced_notice = Column(Boolean)
    claim_type = Column(Enum('ACCIDENT', 'DEATH'))
