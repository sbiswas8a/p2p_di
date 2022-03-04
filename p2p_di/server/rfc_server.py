import contextlib
import datetime
from email.mime import base
from math import inf
from threading import Thread, Lock
from typing import Any, Dict, Boolean
from p2p_di.rfc_client import RFC_Index
from p2p_di.server.server import Server
from p2p_di.utils.message import Message, MessageType, MethodType, StatusCodes
from p2p_di.utils.utils import DEFAULT_RS_PORT, DEFAULT_UPDATE_INTERVAL, Peer_Entry, BadFormatException, NotRegisteredException, get_rfc_data, log, send, receive, find_free_port, get_rs_address
import sys
import socket
import os
import tinydb
from random import randint


class RFC_Server(Server):

    # constructor
    # set clean to false to have server use existing log
    def __init__(self, client_name, client_rfc_index: RFC_Index, clean=True, port: int = None) -> None:
        super().__init__()
        self.client_rfc_index = client_rfc_index
        self.lock = Lock()

        base_path = os.path.dirname(__file__)
        log_path = os.path.join(
            base_path, '..', '..', 'assets', 'peer', client_name, 'rfc_server_log.txt')
        self.log_filename = log_path

        if clean:
            with contextlib.suppress(FileNotFoundError):
                with open(self.log_filename, 'w') as file:
                    now = datetime.datetime.now()
                    file.write('New log for RFC server created at:',
                               now.isoformat())
        else:
            with open(self.log_filename, 'a') as file:
                now = datetime.datetime.now()
                file.write('New RFC server instance created at:',
                           now.isoformat())
        self.startup(port)

    # Adding default port in override
    def startup(self, port=None, period=inf) -> None:
        self.port: int = port
        if port == None:
            self.port = find_free_port()
            log(self.log_filename, 'Using free port {}!'.format(
                self.port), type='info')
        super().startup(self.port, period)
        log(self.log_filename, 'Server listening at port {}!'.format(
            self.port), type='info')

    # server_owner is name + random int, not ip
    def register(self, server_owner: str, current_cookie: str = None) -> str:
        message = Message(MessageType.REQUEST_SERVER)
        message.method = MethodType.REGISTER.name
        message.headers['hostname'] = self.host
        if current_cookie:
            message.headers['cookie'] = current_cookie
        message.data = {'name': server_owner,
                        'hostname': self.host, 'port': self.port}
        rs_address = get_rs_address()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
                conn.connect(rs_address)
                send(conn, message.to_bytes())
                response_bytes = receive(conn)
                response_dict = Message.bytes_to_dict(response_bytes)
                if response_dict['message_type'] != MessageType.SERVER_RESPONSE.name:
                    log(self.log_filename,
                        'Response sent by registration server might be invalid!', type='warning')
                if response_dict['status_code'] != StatusCodes.SUCCESS.value:
                    raise Exception(
                        'Server indicated - {}'.format(response_dict['status_code']))
                response_data = response_dict['data']
                rs_cookie = response_data['cookie']
        except KeyError as e:
            log(self.log_filename, 'Missing data from server response: {}'.format(
                e), type='error')
            return
        except (socket.error, Exception) as e:
            log(self.log_filename,
                'Could not register on server! : {}'.format(e), type='error')
            return
        log(self.log_filename, 'Registered as client @ {}:{}'.format(
            rs_address[0], rs_address[1]), type='info')
        return rs_cookie

    # helper function used for leave / keep alive / pquery
    # returns list if pquery
    def server_requester(self, cookie: str, method: MethodType, log_entries: Dict[str]) -> Any:
        message = Message(MessageType.REQUEST_SERVER)
        message.method = method.name
        message.headers['hostname'] = self.host
        message.headers['cookie'] = cookie
        rs_address = get_rs_address()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
                conn.connect(rs_address)
                send(conn, message.to_bytes())
                response_bytes = receive(conn)
                response_dict = Message.bytes_to_dict(response_bytes)
                if response_dict['message_type'] != MessageType.SERVER_RESPONSE.name:
                    log(self.log_filename,
                        'Response sent by registration server might be invalid!', type='warning')
                if response_dict['status_code'] != StatusCodes.SUCCESS.value:
                    raise Exception(
                        'Server indicated - {}'.format(message.status_code))
                if method == MethodType.PQUERY:
                    try:
                        data = response_dict['data']
                        peer_list = eval(data)
                    except KeyError as ke:
                        log(self.log_filename, 'No peer list data returned in server response: {}'.format(
                            ke), type='error')
                        return
                    except SyntaxError as se:
                        log(self.log_filename, 'Error while parsing peer list returned by server: {}'.format(
                            ke), type='error')
                        return
        except (socket.error, Exception) as e:
            log(self.log_filename, '{} : {}'.format(
                log_entries['failure'], e), type='error')
            return
        log(self.log_filename, log_entries['success'], type='info')
        if method == MethodType.PQUERY:
            return peer_list

    # Overridden from parent class
    def process_new_connection(self, peer_socket: socket.socket, peer_address: socket._RetAddress) -> None:
        try:
            received = receive(peer_socket)
        except (socket.error, Exception) as e:
            log(self.log_filename, str(e), type='error')
            response = self.create_error_response(
                e, StatusCodes.INTERNAL_ERROR)
            send(peer_socket, response.to_bytes())
            return
        try:
            message_dict = Message.bytes_to_dict(received)
            if message_dict['message_type'] != MessageType.REQUEST_PEER.name:
                raise BadFormatException('Incorrect message type!')
            else:
                method_type = message_dict['method_type']
                if method_type == MethodType.RFC_QUERY.name:
                    self.send_rfc_index(peer_socket, peer_address)
                elif method_type == MethodType.GET_RFC.name:
                    self.send_rfc(message_dict, peer_socket, peer_address)
                else:
                    raise BadFormatException('Method type not supported!')
        except Exception as e:
            log(self.log_filename, 'Invalid message received from peer: {}'.format(
                str(e)), type='error')
            response = self.create_error_response(e, StatusCodes.BAD_REQUEST)
            send(peer_socket, response.to_bytes())
            return

    def send_rfc_index(self, peer_socket: socket.socket, peer_address: socket._RetAddress) -> None:
        self.lock.acquire()
        try:
            response = Message(MessageType.PEER_RESPONSE)
            response.headers['hostname'] = self.host
            response.data = str(self.client_rfc_index)
            response.status_code = StatusCodes.SUCCESS.value
            sent = True
        except Exception as ie:
            log(self.log_filename, 'Internal error occurred while sending RFC index : {}'.format(
                ie), type='error')
            response.data = 'Unexpected error occurred!'
            response.status_code = StatusCodes.INTERNAL_ERROR.value
            sent = False
        try:
            send(peer_socket, response.to_bytes())
        except (socket.error, Exception) as e:
            log(self.log_filename,
                'Failed to send response to peer - {}'.format(e), type='error')
            sent = False
        finally:
            self.lock.release()
            if sent:
                log(self.log_filename, 'Successfully sent RFC Index to {}:{}'.format(
                    peer_address[0], peer_address[1]), type='info')

    def send_rfc(self, message_dict: Dict, peer_socket: socket.socket, peer_address: socket._RetAddress) -> None:
        self.lock.acquire()
        response = Message(MessageType.PEER_RESPONSE)
        response.headers['hostname'] = self.host
        response.status_code = StatusCodes.SUCCESS.value
        try:
            rfc_requested = message_dict['data']
            if not self.client_rfc_index.is_owned(rfc_requested):
                raise Exception('Requested RFC not found!')
            else:
                rfc_store: str = self.client_rfc_index.rfc_store
                rfc_path = os.path.join(rfc_store, rfc_requested)
                response.data = get_rfc_data(rfc_path)
        except KeyError as ke:
            log(self.log_filename, 'Bad request made by peer @ {}:{}'.format(
                peer_address[0], peer_address[1]), type='error')
            response.status_code = StatusCodes.BAD_REQUEST.value
            response.data = ke
        except Exception as e:
            log(self.log_filename, '{} requested by peer @ {}:{} not found!'.format(
                rfc_requested, peer_address[0], peer_address[1]), type='error')
            response.status_code = StatusCodes.NOT_FOUND.value
            response.data = e
        finally:
            if response.status_code == StatusCodes.SUCCESS.value:
                log(self.log_filename, '{} sent to peer @ {}:{}'.format(rfc_requested,
                    peer_address[0], peer_address[1]), type='error')
            send(peer_socket, response.to_bytes())
