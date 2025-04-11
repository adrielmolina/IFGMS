from sqlalchemy import Column, Integer, String, Date, DateTime, func
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
 


