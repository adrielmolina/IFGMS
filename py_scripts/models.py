from sqlalchemy import Column, Integer, String, Date, Boolean, Text, DateTime, func, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Accounts(Base):
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

 


