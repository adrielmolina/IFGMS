from py_scripts import db_conn, tools, models
import socket
import time
import requests


def test_db_connection_time():
    import time

    start = time.time()
    db_session = db_conn.SessionLocal()
    
    records = db_session.query(models.Records).all()
    end = time.time()

    print(f"DB QUERY TOOK: {end - start:.4f} seconds")
    
def test_db_latency():
    host = "turntable.proxy.rlwy.net"   # from your URI
    port = 19084                        # from your URI

    t1 = time.time()
    s = socket.socket()
    try:
        s.settimeout(5)
        s.connect((host, port))
        t2 = time.time()
        latency = round(t2 - t1, 4)
        s.close()
        return {"tcp_latency_sec": latency}
    except Exception as e:
        return {"error": str(e)}

def target_vs_actual_test():
    target_vs_actual = db_conn.get_report_target_vs_actual(2025)
    print('target vs actual:',target_vs_actual)

def test_domain():

    url = "https://maab.prc-cavite.org/"
    start = time.time()
    r = requests.get(url)
    end = time.time()

    print(f"Status: {r.status_code}, Total time: {end-start:.4f}s")

def get_claim_id_test():
    claim_id = db_conn.get_claim_id()
    print("New claim ID:", claim_id)

def mailjet_test():
    """
    This call sends an email to one recipient with an additional SMTP header
    """
    from mailjet_rest import Client
    import os
    api_key = '4114a70cf79318eff0303b28859ad89c'
    api_secret = '5120feed68c8bf4fd32bb7cc25d4f50e'
    mailjet = Client(auth=(api_key, api_secret), version='v3.1')
    data = {
    'Messages': [
                    {
                            "From": {
                                    "Email": "pilot@mailjet.com",
                                    "Name": "Mailjet Pilot"
                            },
                            "To": [
                                    {
                                            "Email": "passenger1@mailjet.com",
                                            "Name": "passenger 1"
                                    }
                            ],
                            "Subject": "Your email flight plan!",
                            "TextPart": "Dear passenger 1, welcome to Mailjet! May the delivery force be with you!",
                            "HTMLPart": "<h3>Dear passenger 1, welcome to <a href=\"https://www.mailjet.com/\">Mailjet</a>!<br />May the delivery force be with you!",
                            "Headers": {
                                    "X-My-header": "X2332X-324-432-534"
                            }
                    }
            ]
    }
    result = mailjet.send.create(data=data)
    print (result.status_code)
    
    print(result.json())

def check_pass():
    passw = tools.check_password('q', '$2b$12$5fYrn4y8MtlDhc85UxMHdeRzYkBK4Lm4B4jK9fGcJeesiCZFRP3UK')
    print('Password match:', passw)
    
if __name__ == "__main__":
    #test_db_connection_time()
    #print(test_db_latency())
    #test_domain()
    #get_claim_id_test()
    #mailjet_test()
    
    #target_vs_actual_test()
    check_pass()
    