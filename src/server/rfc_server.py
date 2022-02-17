import sys
from server.server import Server

import socket
import os
import tinydb


class RFC_Server(Server):

    # constructor
    def __init__(self, name) -> None:
        super.__init__()
        self.log = self.log = tinydb.TinyDB('../../assets/server/{client}_rfc_server_log.json'.format(client=name))

    # Overridden from parent class
    def process_new_connection(client_socket, client_address) -> None:
        pass