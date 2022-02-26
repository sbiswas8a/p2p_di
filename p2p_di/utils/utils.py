import time
import socket
import tinydb

DEFAULT_TTL = 7200
DEFAULT_RS_PORT = 65234
DEFAULT_UPDATE_INTERVAL = 5

# returns tuple to be used with socket.connect()
def get_rs_address():
    host = socket.gethostbyname(socket.gethostname()+".local")
    return (host, DEFAULT_RS_PORT)

# Class for messages across clients and servers
class Message():

    def __init__(self) -> None:
        pass

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

    def decrement_ttl(self) -> int:
        self.ttl -= DEFAULT_UPDATE_INTERVAL
        if self.ttl <= 0:
            self.ttl = 0
            self.active = False

    def is_active(self):
        return self.active

    def to_dict():
        pass

    
