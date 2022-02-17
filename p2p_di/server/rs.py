from math import inf
from p2p_di.server.server import Server
import sys
import socket
import os
import tinydb

# RegistrationServer, child class of Server
class RegistrationServer(Server):

    # constructor
    # can pass in file for list of peers known to server
    def __init__(self) -> None:
        super().__init__()
        self.log = tinydb.TinyDB('../../assets/rs/rs_log.json')
        self.peers_db = tinydb.TinyDB('../../assets/rs/peer_list.json')

    # Adding default port in override
    def startup(self, port=65234, period=inf) -> None:
        super().startup()

    # Overridden from parent class
    def process_new_connection(client_socket, client_address) -> None:
        pass

    # overridden from parent class
    # goes through peer list to make any updates
    def update_state() -> None:
        pass
