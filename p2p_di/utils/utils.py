import time
import socket
import tinydb
import logging

DEFAULT_TTL = 7200
DEFAULT_RS_PORT = 65234
DEFAULT_UPDATE_INTERVAL = 5

# returns tuple to be used with socket.connect()
def get_rs_address():
    host = socket.gethostbyname(socket.gethostname()+".local")
    return (host, DEFAULT_RS_PORT)

def log(filename, log_entry, type):
    logging.basicConfig(filename=filename,
                            filemode='a',
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=logging.DEBUG)
    if type == 'info':
        logging.info(log_entry)
    elif type == 'error':
        logging.error(log_entry)
    elif type == 'debug':
        logging.debug(log_entry)

# Class for entry in peer list 
# maintained by the registration server
class Peer_Entry():
    
    def __init__(self, cookie, name, port, last_active=None, registration_number=1) -> None:
        self.name = name
        self.cookie = cookie
        self.port = port
        if last_active == None:
            self.active = True
            self.last_active = time.time()
            self.ttl = DEFAULT_TTL
        else:
            self.active = False
            self.last_active = last_active
            self.ttl = 0
        self.registration_number = registration_number

    def decrement_ttl(self, interval=DEFAULT_UPDATE_INTERVAL) -> None:
        self.ttl -= interval
        if self.ttl <= 0:
            self.ttl = 0
            self.active = False

    def is_active(self):
        return self.active

    # returns dict that can be inserted in tinydb
    def to_dict(self) -> dict:
        db_entry ={}
        db_entry['cookie'] = self.cookie
        db_entry['name'] = self.name
        db_entry['port'] = self.port
        db_entry['last_active'] = self.last_active
        db_entry['registration_number'] = self.registration_number
        return db_entry

    
