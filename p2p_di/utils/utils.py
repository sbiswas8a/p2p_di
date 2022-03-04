import time
import socket
from typing import Any, List, Tuple
from pyparsing import line
import tinydb
import logging
from contextlib import closing
from struct import pack, unpack

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
    elif type == 'warning':
        logging.warning(log_entry)
    elif type == 'error':
        logging.error(log_entry)
    elif type == 'debug':
        logging.debug(log_entry)

# finds and returns a free port for client's rfc server


def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

# returns list of strings where each element is one line of rfc text file


def get_rfc_data(rfc_path: str) -> List[str]:
    rfc_lines = []
    with open(rfc_path, 'rb') as rfc_file:
        while line := rfc_file.readline().strip():
            rfc_lines.append(line)
    return rfc_lines

# writes list of strings to text file


def save_rfc_file(lines: List[str], rfc_path: str) -> None:
    rfc_lines = []
    with open(rfc_path, 'w') as rfc_file:
        rfc_file.write('\n'.join(lines))


def send(conn: socket.socket, data: bytes):
    data_plus_len = pack('>I', len(data)) + data
    conn.sendall(data_plus_len)


def receive(conn: socket.socket) -> bytes:
    data_len = unpack('>I', conn.recv(4))[0]
    received_data = b''
    left_to_receive = data_len
    while left_to_receive != 0:
        received_data += conn.recv(left_to_receive)
        left_to_receive = data_len - len(received_data)
    return received_data

# Class for entry in peer list
# maintained by the registration server


class Peer_Entry():

    def __init__(self, cookie, name, hostname, port, last_active=None, registration_number=1) -> None:
        self.cookie = cookie
        self.name = name
        self.hostname = hostname
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

    def re_register(self, port) -> None:
        self.keep_alive()
        self.port = port
        self.registration_number += 1

    def keep_alive(self) -> None:
        self.last_active = time.time()
        self.active = True
        self.ttl = DEFAULT_TTL

    def mark_inactive(self) -> None:
        self.last_active = time.time()
        self.active = False
        self.ttl = 0

    def decrement_ttl(self, interval=DEFAULT_UPDATE_INTERVAL) -> None:
        self.ttl -= interval
        if self.ttl <= 0:
            self.ttl = 0
            self.active = False

    def is_active(self):
        return self.active

    # returns dict that can be inserted in tinydb
    def to_dict(self) -> dict:
        db_entry = {}
        db_entry['cookie'] = self.cookie
        db_entry['name'] = self.name
        db_entry['hostname'] = self.hostname
        db_entry['port'] = self.port
        db_entry['last_active'] = self.last_active
        db_entry['registration_number'] = self.registration_number
        return db_entry

# exception for when message sent is
# not in the correct format


class BadFormatException(Exception):
    pass

# when client not registered on RS makes a request


class NotRegisteredException(Exception):
    pass
