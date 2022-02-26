from math import inf
from threading import Thread, Lock
import time, datetime
from p2p_di.server.server import Server
from p2p_di.utils.utils import DEFAULT_RS_PORT, DEFAULT_UPDATE_INTERVAL, Peer_Entry, log
import sys
import socket
import os
import tinydb
import contextlib
from uuid import uuid4 as cookie

# RegistrationServer, child class of Server
class RegistrationServer(Server):

    # constructor
    # can pass in file for list of peers known to server
    # set clean to false to have server use existing log / peer list
    def __init__(self, clean=True) -> None:
        super().__init__()
        self.lock = Lock()
        self.peers = {}
        self.peers_db = tinydb.TinyDB('../../assets/rs/peer_list.json')
        self.log_filename = '../../assets/rs/rs_log.txt'

        if clean:
            with contextlib.suppress(FileNotFoundError):
                os.remove('../../assets/rs/peer_list.json')
                os.remove('../../assets/rs/rs_log.txt')
                with open(self.log_filename, 'w') as file:
                    now = datetime.datetime.now()
                    file.write('New log created at:', now.isoformat())
        else:
            self.load_peers()
            with open(self.log_filename, 'a') as file:
                    now = datetime.datetime.now()
                    file.write('New server instance created at:', now.isoformat())

        self.startup()

    # Adding default port in override
    def startup(self, port=DEFAULT_RS_PORT, period=inf) -> None:
        self.update_loop_running = True
        self.update_thread = Thread(target=self.periodic_updater, args=(DEFAULT_UPDATE_INTERVAL, self.update_loop), daemon=False)
        self.update_thread.start()
        super().startup(port, period)


    # Overridden from parent class
    def process_new_connection(client_socket, client_address) -> None:
        pass

    # runs a function periodically
    def periodic_updater(self, delay, update_function) -> None:
        interval = delay
        next_run_time = time.time() + delay
        while True:
            time.sleep(max(0, next_run_time - time.time()))
            try:
                update_function(interval)
            except Exception as e:
                log(self.log_filename, str(e), type='error')
            #skips task if behind schedule, updates interval to reflect time difference
            interval = (time.time() - next_run_time) // delay * delay + delay  
            next_run_time += interval

    # goes through peer list to make any updates
    def update_loop(self, interval) -> None:
        self.lock.acquire()
        for index in self.peers:
            peer = self.peers[index]
            if peer.is_active():
                peer.decrement_ttl(interval)
        self.lock.release()

    # go through peer list and update their status
    def load_peers(self):
        existing_peers = self.peers_db.all()
        for peer_data in existing_peers:
            peer = Peer_Entry(peer_data['cookie'], peer_data['name'], peer_data['port'], peer_data['last_active'], peer_data['registration_number'])
        self.peers[peer_data['cookie']] = peer

    # stop the server
    def stop(self):
        self.update_loop_running = False
        self.update_thread.join()
        super().stop()