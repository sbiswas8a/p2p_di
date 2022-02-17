import sys
from server.server import Server

import socket
import os
import tinydb


class RegistrationServer(Server):

    def load_or_create_db():
        pass

    # constructor
    # can pass in file for list of peers known to server
    def __init__(self, peer_list=None, port=None) -> None:
        super.__init__()
        self.load_or_create_db()
        self.log = tinydb.TinyDB('../../assets/server/rs_log.json')

    # Overridden from parent class
    def process_new_connection(client_socket, client_address) -> None:
        pass