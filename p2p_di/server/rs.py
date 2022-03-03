from math import inf
from threading import Thread, Lock
import time
import datetime
from p2p_di.server.server import Server
from p2p_di.utils.message import Message, MessageType, MethodType, StatusCodes
from p2p_di.utils.utils import DEFAULT_RS_PORT, DEFAULT_UPDATE_INTERVAL, Peer_Entry, BadFormatException, NotRegisteredException, log, send, receive
import socket
import os
import tinydb
import contextlib
from uuid import uuid4

# RegistrationServer, child class of Server


class RegistrationServer(Server):

    # constructor
    # set clean to false to have server use existing log / peer list
    def __init__(self, clean=True) -> None:
        super().__init__()
        self.lock = Lock()
        self.peers = {}

        base_path = os.path.dirname(__file__)
        db_path = os.path.join(base_path, '..', '..', 'assets', 'rs', 'peer_list.json')
        self.peers_db = tinydb.TinyDB(db_path)
        self.log_filename = os.path.join(base_path, '..', '..', 'assets', 'rs', 'rs_log.txt')

        if clean:
            with contextlib.suppress(FileNotFoundError):
                self.peers_db.truncate()
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
        self.update_thread = Thread(target=self.periodic_updater, args=(
            DEFAULT_UPDATE_INTERVAL, self.update_loop), daemon=False)
        self.update_thread.start()
        super().startup(port, period)

    # Overridden from parent class
    def process_new_connection(self, client_socket: socket.socket, client_address: socket._RetAddress) -> None:
        try:
            received = receive(client_socket)
        except Exception as e:
            log(self.log_filename, str(e), type='error')
            response = self.create_error_response(
                e, StatusCodes.INTERNAL_ERROR)
            send(client_socket, response.to_bytes())
            return
        try:
            message_dict = Message.bytes_to_dict(received)
            if message_dict['message_type'] != MessageType.REQUEST_SERVER.name:
                raise BadFormatException('Incorrect message type!')
            else:
                method_type = message_dict['method_type']
                if method_type == MethodType.REGISTER.name:
                    self.register_client(
                        message_dict, client_socket, client_address)
                elif method_type == MethodType.LEAVE.name:
                    self.mark_inactive(
                        message_dict, client_socket, client_address)
                elif method_type == MethodType.KEEP_ALIVE.name:
                    self.keep_alive(
                        message_dict, client_socket, client_address)
                elif method_type == MethodType.PQUERY.name:
                    self.peers_query(
                        message_dict, client_socket, client_address)
                else:
                    raise BadFormatException('Method type not supported!')
        except Exception as e:
            log(self.log_filename, str(e), type='error')
            response = self.create_error_response(e, StatusCodes.BAD_REQUEST)
            send(client_socket, response.to_bytes())
            return

    def register_client(self, message_dict: dict, client_socket: socket.socket, client_address: socket._RetAddress):
        response = Message(MessageType.SERVER_RESPONSE)
        client_cookie, client_hostname, client_port = ''
        self.lock.acquire()
        try:
            client_data = message_dict['data']
            client_name = client_data['name']
            client_hostname = client_data['hostname']
            client_port = client_data['port']
            # If known client re-registering
            if 'cookie' in message_dict and message_dict['cookie'] in self.peers:
                client_cookie = message_dict['cookie']
                peer_entry: Peer_Entry = self.peers[client_cookie]
                peer_entry.re_register(client_port)
                client_last_active = peer_entry.last_active
                client_registration_number = peer_entry.registration_number
                Peer = tinydb.Query()
                tinydb.TinyDB.update({'port': client_port, 'last_active': client_last_active,
                                     'registration_number': client_registration_number}, Peer.cookie == client_cookie)
            else:  # new client registering
                client_cookie : str = uuid4().hex
                peer_entry = Peer_Entry(
                    client_cookie, client_name, client_hostname, client_port)
                self.peers[client_cookie] = peer_entry
                tinydb.TinyDB.insert(peer_entry.to_dict())
            # success response
            response.headers['hostname'] = self.host
            response.data['cookie'] = client_cookie
            response.status_code = StatusCodes.SUCCESS
        except Exception as e:
            log(self.log_filename, str(e), type='error')
            response = self.create_error_response(e, StatusCodes.BAD_REQUEST)
        finally:
            self.lock.release()
            send(client_socket, response.to_bytes())
            if response.status_code == StatusCodes.SUCCESS:
                log(self.log_filename, 'Registered new client: {}:{}'.format(client_hostname, client_port), type="info")
            else:
                log(self.log_filename, 'Failed to register new client: {}'.format(client_hostname), type="info")


    def mark_inactive(self, message_dict: dict, client_socket: socket.socket, client_address: socket._RetAddress):
        response = Message(MessageType.SERVER_RESPONSE)
        self.lock.acquire()
        try:
            client_hostname = message_dict['hostname']
            # if cookie not provided or if cookie not recognized
            if 'cookie' in message_dict:
                client_cookie = message_dict['cookie']
                if not client_cookie in self.peers:
                    raise NotRegisteredException('You are not registered on this server!')
            else:
                raise BadFormatException('Cookie not provided. Include assigned cookie in request!')
            peer_entry: Peer_Entry = self.peers[client_cookie]
            peer_entry.mark_inactive()
            client_last_active = peer_entry.last_active
            Peer = tinydb.Query()
            tinydb.TinyDB.update(
                {'last_active': client_last_active}, Peer.cookie == client_cookie)
            # success response
            response.headers['hostname'] = self.host
            response.headers['cookie'] = client_cookie
            response.status_code = StatusCodes.SUCCESS
        except NotRegisteredException as nre:
            log(self.log_filename, str(nre), type='error')
            response = self.create_error_response(nre, StatusCodes.FORBIDDEN)
        except Exception as e:
            log(self.log_filename, str(e), type='error')
            response = self.create_error_response(e, StatusCodes.BAD_REQUEST)
        finally:
            self.lock.release()
            send(client_socket, response.to_bytes())
            log(self.log_filename, '{} left server'.format(
                client_hostname), type="info")

    def keep_alive(self, message_dict: dict, client_socket: socket.socket, client_address: socket._RetAddress):
        response = Message(MessageType.SERVER_RESPONSE)
        self.lock.acquire()
        try:
            client_hostname = message_dict['hostname']
            # if cookie not provided or if cookie not recognized
            if 'cookie' in message_dict:
                client_cookie = message_dict['cookie']
                if not client_cookie in self.peers or not self.peers[client_cookie].is_active():
                    raise NotRegisteredException(
                        'Please re-register on the server.')
            else:
                raise BadFormatException(
                    'Cookie not provided. Include assigned cookie in request!')
            peer_entry: Peer_Entry = self.peers[client_cookie]
            peer_entry.keep_alive()
            client_last_active = peer_entry.last_active
            Peer = tinydb.Query()
            tinydb.TinyDB.update(
                {'last_active': client_last_active}, Peer.cookie == client_cookie)
            # success response
            response.headers['hostname'] = self.host
            response.headers['cookie'] = client_cookie
            response.status_code = StatusCodes.SUCCESS
        except NotRegisteredException as nre:
            log(self.log_filename, str(nre), type='error')
            response = self.create_error_response(nre, StatusCodes.FORBIDDEN)
        except Exception as e:
            log(self.log_filename, str(e), type='error')
            response = self.create_error_response(e, StatusCodes.BAD_REQUEST)
        finally:
            self.lock.release()
            send(client_socket, response.to_bytes())
            log(self.log_filename, '{} ttl reset!'.format(
                client_hostname), type="info")

    def peers_query(self, message_dict: dict, client_socket: socket.socket, client_address: socket._RetAddress):
        response = Message(MessageType.SERVER_RESPONSE)
        self.lock.acquire()
        try:
            client_hostname = message_dict['hostname']
            # if cookie not provided or if cookie not recognized
            if not 'cookie' in message_dict or not message_dict['cookie'] in self.peers:
                raise NotRegisteredException(
                    'You are not registered on this server!')
            client_cookie = message_dict['cookie']
            # marking alive on last action
            peer_entry: Peer_Entry = self.peers[client_cookie]
            peer_entry.keep_alive()
            client_last_active = peer_entry.last_active
            Peer = tinydb.Query()
            tinydb.TinyDB.update(
                {'last_active': client_last_active}, Peer.cookie == client_cookie)
            # success response
            response.data = str(self.get_active_peers())
            response.headers['hostname'] = self.host
            response.headers['cookie'] = client_cookie
            response.status_code = StatusCodes.SUCCESS
        except NotRegisteredException as nre:
            log(self.log_filename, str(nre), type='error')
            response = self.create_error_response(nre, StatusCodes.FORBIDDEN)
        except Exception as e:
            log(self.log_filename, str(e), type='error')
            response = self.create_error_response(e, StatusCodes.BAD_REQUEST)
        finally:
            self.lock.release()
            send(client_socket, response.to_bytes())
            log(self.log_filename,
                'Sent list of active peers to client @ {}'.format(client_hostname), type="info")

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
            # skips task if behind schedule, updates interval to reflect time difference
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
            peer = Peer_Entry(peer_data['cookie'], peer_data['name'], peer_data['port'],
                              peer_data['last_active'], peer_data['registration_number'])
        self.peers[peer_data['cookie']] = peer

    def get_active_peers(self) -> list:
        active = []
        peer_entry: Peer_Entry
        for peer_entry in self.peers.values():
            if peer_entry.is_active():
                active.append('{}:{}'.format(
                    peer_entry.hostname, peer_entry.port))
        return active

    # stop the server
    def stop(self):
        self.update_loop_running = False
        self.update_thread.join()
        super().stop()
