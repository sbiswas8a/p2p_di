import contextlib
import datetime
from math import inf
from threading import Lock
from p2p_di.server.server import Server
from p2p_di.utils.utils import find_free_port
import sys
import socket
import os
import tinydb
from random import randint

class RFC_Server(Server):

    # constructor
    # set clean to false to have server use existing log
    def __init__(self, client_name, clean=True) -> None:
        super().__init__()
        self.lock = Lock()
        self.log_filename = '../../assets/rs/{}_{}_rfc_server_log.txt'.format(client_name, randint(0,999))

        if clean:
            with contextlib.suppress(FileNotFoundError):
                os.remove('../../assets/rs/rs_log.txt')
                with open(self.log_filename, 'w') as file:
                    now = datetime.datetime.now()
                    file.write('New log created at:', now.isoformat())
        else:
            with open(self.log_filename, 'a') as file:
                    now = datetime.datetime.now()
                    file.write('New server instance created at:', now.isoformat())

        self.startup()

    # Adding default port in override
    def startup(self, port=0, period=inf) -> None:
        self.port = port
        if port == 0:
            self.port = find_free_port()
        super().startup(port, period)

    # Overridden from parent class
    def process_new_connection(client_socket, client_address) -> None:
        pass