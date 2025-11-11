from sqlalchemy import Column, Integer, String, Date, DECIMAL, Boolean, Text, ForeignKey, Enum, SmallInteger, DateTime, TIMESTAMP, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from flask_login import UserMixin

Base = declarative_base()


class Accounts(Base, UserMixin):
    __tablename__ = 'accounts'

    account_id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False)
    password = Column(String(255))
    email = Column(String(255), unique=True)
    first_name = Column(String(255))
    middle_name = Column(String(255))
    last_name = Column(String(255))
    suffix = Column(String(255))
    birth_date = Column(Date)
    contact_no = Column(String(255))
    acct_created = Column(Date)
    office_location = Column(String(255))
    user_level = Column(Enum('staff', 'admin', 'superadmin'))
    acct_status = Column(String(255))
    acct_review_date = Column(Date)
    profile_pic = Column(LargeBinary, nullable=True)
    

    def get_id(self):
        # (default is id, so override it for account_id)
        return str(self.account_id)

    @property
    def birth_date_YMD(self):
        return self.birth_date.strftime('%Y-%m-%d') if self.birth_date else None
    
    @property
    def acct_created_YMD(self):
        return self.acct_created.strftime('%Y-%m-%d') if self.acct_created else None
    
    @property
    def acct_review_date_YMD(self):
        return self.acct_review_date.strftime('%Y-%m-%d') if self.acct_review_date else None
    
    def to_dict(self):
        return {
            'account_id': self.account_id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'last_name': self.last_name,
            'suffix': self.suffix,
            'birth_date': self.birth_date.strftime('%Y-%m-%d') if self.birth_date else None,
            'contact_no': self.contact_no,
            'acct_created': self.acct_created.strftime('%Y-%m-%d') if self.acct_created else None,
            'office_location': self.office_location,
            'user_level': self.user_level,
            'acct_status': self.acct_status,
            'acct_review_date': self.acct_review_date.strftime('%Y-%m-%d') if self.acct_review_date else None
        }

class OTPs(Base):
    __tablename__ = 'otp_verifications'
    
    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    email = Column(String(255),  nullable=False)
    otp = Column(String(6),  nullable=False)
    expires_at = Column(DateTime,  nullable=False)
    created_at = Column(TIMESTAMP,  nullable=False)
    otp_used = Column(Boolean, default=False)
    
    

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
    
    @property
    def declaration_date_YMD(self):
        return self.declaration_date.strftime('%Y-%m-%d') if self.declaration_date else None

    @property
    def effectivity_date_YMD(self):
        return self.effectivity_date.strftime('%Y-%m-%d') if self.effectivity_date else None
    
    def to_dict(self):
        return {
            'record_id': self.record_id,
            'year': self.year,
            'id_received': self.id_received,
            'declared': self.declared,
            'declaration_date': self.declaration_date_YMD,
            'effectivity_date': self.effectivity_date_YMD,
            'location_particular': self.location_particular,
            'location_category': self.location_category,
            'municipality': self.municipality,
            'district': self.district,
            'paid': self.paid,
            'origin': self.origin,
            'remarks': self.remarks,
            'tags': self.tags
        }
    

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
    dispatch_ready = Column(Boolean)
    dispatch_id = Column(Integer, ForeignKey('dispatch.dispatch_id'))
    
    @property
    def declaration_date_YMD(self):
        return self.declaration_date.strftime('%Y-%m-%d') if self.declaration_date else None
    
    @property
    def or_date_YMD(self):
        return self.OR_date.strftime('%Y-%m-%d') if self.OR_date else None


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

    @property
    def birth_date_YMD(self):
        return self.birth_date.strftime('%Y-%m-%d') if self.birth_date else None

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
    
    @property
    def date_filed_YMD(self):
        return self.date_filed.strftime('%Y-%m-%d') if self.date_filed else None

    @property
    def date_of_loss_YMD(self):
        return self.date_of_loss.strftime('%Y-%m-%d') if self.date_of_loss else None
    
    @property
    def date_released_YMD(self):
        return self.date_released.strftime('%Y-%m-%d') if self.date_released else None
    
    @property
    def date_picked_up_YMD(self):   
        return self.date_picked_up.strftime('%Y-%m-%d') if self.date_picked_up else None
    
    def to_dict(self):
        return {
            'claim_id': self.claim_id,
            'date_filed': self.date_filed_YMD,
            'received_by': self.received_by,
            'claim_origin': self.claim_origin,
            'date_of_loss': self.date_of_loss_YMD,
            'maab_no': self.maab_no,
            'same_as_insured': self.same_as_insured,
            'claimant_first_name': self.claimant_first_name,
            'claimant_middle_name': self.claimant_middle_name,
            'claimant_last_name': self.claimant_last_name,
            'claimant_suffix': self.claimant_suffix,
            'relation_to_insured': self.relation_to_insured,
            'claimant_contact_no': self.claimant_contact_no,
            'claimant_email': self.claimant_email,
            'claim_remarks': self.claim_remarks,
            'status': self.status,
            'date_released': self.date_released_YMD,
            'chinabank_check_no': self.chinabank_check_no,
            'chinabank_amount': float(self.chinabank_amount) if self.chinabank_amount is not None else None,
            'bpi_check_no': self.bpi_check_no,
            'bpi_amount': float(self.bpi_amount) if self.bpi_amount is not None else None,
            'release_remarks': self.release_remarks,
            'scanned_docs': self.scanned_docs,
            'prm_file': self.prm_file,
            'quit_claim_file': self.quit_claim_file,
            'picked_up': self.picked_up,
            'date_picked_up': self.date_picked_up_YMD,
            'req_claim_form': self.req_claim_form,
            'req_prc_id': self.req_prc_id,
            'req_med_cert': self.req_med_cert,
            'req_hos_bill_or': self.req_hos_bill_or,
            'req_state_of_acc': self.req_state_of_acc,
            'req_doctor_pres': self.req_doctor_pres,
            'req_purchased_meds': self.req_purchased_meds,
            'req_med_records': self.req_med_records,
            'req_animal_bite_treat_rec': self.req_animal_bite_treat_rec,
            'req_incident_rep': self.req_incident_rep,
            'req_police_rep': self.req_police_rep,
            'req_brgy_rep': self.req_brgy_rep,
            'req_drivers_lic': self.req_drivers_lic,
            'req_birth_cert': self.req_birth_cert,
            'req_marriage_cert': self.req_marriage_cert,
            'req_death_cert': self.req_death_cert,
            'req_burial_receipts': self.req_burial_receipts,
            'sent_advanced_notice': self.sent_advanced_notice,
            'claim_type': self.claim_type
        }
        

class Dispatch(Base):
    __tablename__ = 'dispatch'
    dispatch_id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    dispatch_type = Column(String(255))
    dispatch_origin = Column(String(255))
    dispatch_year = Column(Integer)
    dispatch_cutoff = Column(Date)
    dispatch_status = Column(String(255))
    date_dispatched = Column(Date)
    dispatch_total = Column(DECIMAL(10, 0))
    late_declare = Column(Boolean)
    dispatch_remarks = Column(Text)
    

class Logs(Base):
    __tablename__ = 'audit_logs'

    # !TODO rname action_id to log_id
    action_id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False) 
    date = Column(DateTime)
    staff_name = Column(String(255))
    user_level = Column(Enum('admin', 'staff', 'superadmin'))
    action_name = Column(String(255))
    description = Column(Text)
    account_id = Column(Integer, ForeignKey('accounts.account_id'))


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
