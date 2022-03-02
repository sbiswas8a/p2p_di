import contextlib
import datetime
from email.mime import base
from math import inf
from threading import Thread, Lock
from p2p_di.server.server import Server
from p2p_di.utils.message import Message, MessageType, MethodType, StatusCodes
from p2p_di.utils.utils import DEFAULT_RS_PORT, DEFAULT_UPDATE_INTERVAL, Peer_Entry, BadFormatException, NotRegisteredException, log, send, receive, find_free_port, get_rs_address
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
        self.cookie: str = None
        self.lock = Lock()

        base_path = os.path.dirname(__file__)
        log_path = os.path.join(base_path, '..', '..', 'assets', 'peer', client_name, 'rfc_server_log.txt')
        self.log_filename = log_path

        if clean:
            with contextlib.suppress(FileNotFoundError):
                with open(self.log_filename, 'w') as file:
                    now = datetime.datetime.now()
                    file.write('New log for RFC server created at:', now.isoformat())
        else:
            with open(self.log_filename, 'a') as file:
                    now = datetime.datetime.now()
                    file.write('New RFC server instance created at:', now.isoformat())

        self.startup()

    # Adding default port in override
    def startup(self, port=None, period=inf) -> None:
        self.port: int = port
        if port == None:
            self.port = find_free_port()
        super().startup(port, period)

    # server_owner is name + random int, not ip
    def register(self, server_owner:str):
        message = Message(MessageType.REQUEST_SERVER)
        message.method = MethodType.REGISTER.name
        message.headers['hostname'] = self.host
        if self.cookie:
            message.headers['cookie'] = self.cookie
        message.data = {'name': server_owner, 'hostname': self.host, 'port': self.port}
        rs_address = get_rs_address()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
                conn.connect(rs_address)
                send(conn, message.to_bytes())
                response_bytes = receive(conn)
                response_dict = Message.bytes_to_dict(response_bytes)
                if message.message_type != MessageType.SERVER_RESPONSE.name:
                    log(self.log_filename, 'Response sent by registration server might be invalid!', type='warning')
                try:
                    response_data = response_dict['data']
                    self.cookie = response_data['cookie']
                except KeyError as e:
                    log(self.log_filename, 'Missing data from server response: {}'.format(e), type='error')
        except (socket.error, Exception) as e:
            log(self.log_filename, 'Could not register on server! : {}'.format(e), type='error')

    # Overridden from parent class
    # TODO finish + don't throw exceptions
    def process_new_connection(self, peer_socket: socket.socket, peer_address: socket._RetAddress) -> None:
        try:
            received = receive(peer_socket)
        except (socket.error, Exception) as e:
            log(self.log_filename, str(e), type='error')
            response = self.create_error_response(e, StatusCodes.INTERNAL_ERROR)
            send(peer_socket, response.to_bytes())
            return
        try:
            message_dict = Message.bytes_to_dict(received)
            if message_dict['message_type'] != MessageType.REQUEST_PEER.name:
                raise BadFormatException('Incorrect message type!')
            else:
                method_type = message_dict['method_type']
                if method_type == MethodType.RFC_QUERY.name:
                    self.register_client(message_dict, peer_socket, peer_address)
                elif method_type == MethodType.GET_RFC.name:
                    self.mark_inactive(message_dict, peer_socket, peer_address)
                else:
                    raise BadFormatException('Method type not supported!')
        except Exception as e:
            log(self.log_filename, str(e), type='error')
            response = self.create_error_response(e, StatusCodes.BAD_REQUEST)
            send(peer_socket, response.to_bytes())
            return