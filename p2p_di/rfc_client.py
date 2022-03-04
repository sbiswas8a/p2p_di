from __future__ import annotations

import os
import socket
from random import randint
from shutil import copyfile
from typing import Dict, List
from xmlrpc.client import Boolean

from p2p_di.server.rfc_server import RFC_Server
from p2p_di.utils.message import Message, MessageType, MethodType, StatusCodes
from p2p_di.utils.utils import log, receive, save_rfc_file, send

# class for the entries in RFC_Index


class Index_Entry():

    def __init__(self, owned: bool = False, hosted_on: dict = {}) -> None:
        self.owned = owned
        # in the form {'ip':port}
        self.hosted_on: Dict[str] = hosted_on

    def __str__(self) -> str:
        return str(self.hosted_on)

    def is_owned(self) -> bool:
        return self.owned

    def get_peers_who_own(self) -> Dict[str]:
        return self.hosted_on

    def merge_peer_list(self, other: Index_Entry) -> None:
        self.hosted_on = self.hosted_on | other.hosted_on


class RFC_Index():

    def __init__(self, entries: dict = {}) -> None:
        self.rfc_store: str = None
        self.rfcs: Dict[str, Index_Entry] = entries

    def __str__(self) -> str:
        ri = {}
        for rfc in self.rfcs:
            ri[rfc] = str(self.rfcs[rfc])
        return str(ri)

    def is_owned(self, rfc: str):
        return rfc in self.rfcs and self.rfcs[rfc].is_owned()

    def get_owners(self, rfc: str) -> Dict[str]:
        if rfc not in self.rfcs:
            return {}
        else:
            return self.rfcs[rfc].get_peers_who_own()

    def to_bytes(self) -> bytes:
        return bytes(str(self), 'utf-8')

    def merge_index(self, other: RFC_Index):
        for rfc in other.rfcs:
            if rfc not in self.rfcs:
                self.rfcs[rfc] = other.rfcs[rfc]
            else:
                self.rfcs[rfc].merge_peer_list(other.rfcs[rfc])

    @staticmethod
    def from_string(string: str) -> RFC_Index:
        dict_ie_string: Dict[str, str] = eval(string)
        ri_dict = {}
        for rfc in dict_ie_string:
            ri_dict[rfc] = Index_Entry(False, eval(dict_ie_string[rfc]))
        to_return = RFC_Index(ri_dict)
        return to_return

    @staticmethod
    def from_bytes(bytes: bytes) -> RFC_Index:
        string = bytes.decode('utf-8')
        return RFC_Index.from_string(string)


class Client():

    # name is not hostname
    # @rfcs_owned is filename containing list of rfcs stored locally
    # rfcs_owned must have each rfc owned on a separate line
    def __init__(self, name: str, rfcs_owned_list: str = None, port: int = None) -> None:
        random_int = randint(0, 999)
        self.name = '{}_{}'.format(name, random_int)
        self.cookie: str = None
        self.peer_list: Dict[str, str] = {}
        base_path = os.path.dirname(__file__)
        os.makedirs(os.path.join(base_path, '..', 'assets',
                    'peer', self.name, 'rfc_store'), exist_ok=True)
        self.log_filename = os.path.join(
            base_path, '..', 'assets', 'peer', self.name, 'action_log.txt')
        if rfcs_owned_list:
            rfcs_owned_list = os.path.join(os.getcwd(), rfcs_owned_list)
            self.rfc_index: RFC_Index = self.load_rfcs(rfcs_owned_list)
        else:
            self.rfc_index: RFC_Index = RFC_Index()
        self.rfc_index.rfc_store = os.path.join(
            base_path, '..', 'assets', 'peer', self.name, 'rfc_store')
        self.rfc_server = RFC_Server(self.name, self.rfc_index, True, port)

    # load rfc
    def load_rfcs(self, filename: str) -> RFC_Index:
        owned = RFC_Index()
        base_path = os.path.dirname(__file__)
        if not os.path.isfile(filename):
            return owned
        with open(filename) as file:
            while line := file.readline().strip():
                file_path = os.path.join(base_path, '..', 'rfc_store', line)
                if os.path.isfile(file_path):
                    copyfile(file_path, os.path.join(
                        base_path, '..', 'assets', 'peer', self.name, 'rfc_store', file_path))
                    owned.rfcs[filename] = Index_Entry(filename, True)
        return owned

    def register(self):
        log(self.log_filename, 'Attempting to register on server', type='info')
        self.cookie = self.rfc_server.register(self.name)

    def stay_alive(self):
        log(self.log_filename, 'Pinging server to stay alive', type='info')
        self.rfc_server.server_requester(self.cookie, MethodType.KEEP_ALIVE, {
                                         'success': 'Successfully pinged server!', 'failure': 'Failed to ping server'})

    def query_for_peers(self):
        log(self.log_filename, 'Querying server for peers', type='info')
        peer_strings: List[str] = self.rfc_server.server_requester(
            self.cookie, MethodType.PQUERY, {'success': 'Received peer list from server!'})

        def format_address(address): return (address[0], int(address[1]))
        new_peer_list = dict(format_address(string.split(':')
                             for string in peer_strings))
        self.peer_list = new_peer_list

    def leave_rs(self):
        log(self.log_filename, 'Leaving server', type='info')
        self.rfc_server.server_requester(self.cookie, MethodType.LEAVE, {
                                         'success': 'Successfully updated status!', 'failure': 'Failed to update status'})

    def request_rfc_index(self, peer_hostname: str, peer_port: str):
        log(self.log_filename, "Requesting RFC Index from peer @ {}:{}".format(
            peer_hostname, peer_port), type='info')
        request = Message(MessageType.REQUEST_PEER)
        request.method = MethodType.RFC_QUERY
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            try:
                conn.connect(peer_hostname, peer_port)
                send(conn, request.to_bytes())
                response_bytes = receive(conn)
                response_dict = Message.bytes_to_dict(response_bytes)
                if response_dict['status_code'] != StatusCodes.SUCCESS.value:
                    log(self.log_filename, 'Peer ran into error while sending index - {}'.format(
                        response_dict['data']), type='error')
                    return
                try:
                    peer_rfc_string = response_dict['data']
                    peer_rfc_index: RFC_Index = RFC_Index.from_string(
                        peer_rfc_string)
                    self.rfc_index.merge_index(peer_rfc_index)
                    self.rfc_server.client_rfc_index = self.rfc_index
                    log(self.log_filename, 'Successfully merged RFC Index from peer @ {}:{}'.format(
                        peer_hostname, peer_port), type='info')
                except (KeyError, Exception) as e:
                    log(self.log_filename, 'Invalid index data received from peer @ {}:{} - {}'.format(
                        peer_hostname, peer_port, e), type='error')
                    return
            except (socket.error, Exception) as e:
                log(self.log_filename,
                    'Error while retrieving RFC Index from peer - {}'.format(e), type='error')

    def request_rfc(self, rfc_name, peer_hostname, peer_port) -> Boolean:
        log(self.log_filename, 'Requesting {} from peer @ {}:{}'.format(rfc_name,
            peer_hostname, peer_port), type='info')
        request = Message(MessageType.REQUEST_PEER)
        request.method = MethodType.GET_RFC
        request.data = [rfc_name]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
            try:
                conn.connect(peer_hostname, peer_port)
                send(conn, request.to_bytes())
                response_bytes = receive(conn)
                response_dict = Message.bytes_to_dict(response_bytes)
                if response_dict['status_code'] != StatusCodes.SUCCESS.value:
                    log(self.log_filename, 'Peer ran into error while sending index - {}'.format(
                        response_dict['data']), type='error')
                    return False
                try:
                    requested_rfc = response_dict['data']
                    save_rfc_file(requested_rfc, os.path.join(
                        self.rfc_index.rfc_store, rfc_name))
                    self.rfc_index.rfcs[rfc_name].owned = True
                    log(self.log_filename, 'Successfully received {} from peer!'.format(
                        rfc_name), type='info')
                    return True
                except (KeyError, Exception) as e:
                    log(self.log_filename, 'Invalid rfc file received from peer @ {}:{} - {}'.format(
                        peer_hostname, peer_port, e), type='error')
                    return False
            except (socket.error, Exception) as e:
                log(self.log_filename,
                    'Error while retrieving {} from peer - {}'.format(rfc_name, e), type='error')
                return False

    def find_peers_with_rfc(self, rfc_name: str) -> Dict[str, str]:
        log(self.log_filename, 'Finding peers with {}!'.format(rfc_name), type='info')
        self.query_for_peers()  # refreshing peer list
        for (host, port) in self.peer_list.items():  # refresh rfc index
            self.request_rfc_index(host, port)
        rfc_owners = {}
        if rfc_name not in self.rfc_index.rfcs:
            return rfc_owners
        else:
            return self.rfc_index.rfcs[rfc_name].get_peers_who_own()

    # tries to find rfc, pinging every owner till its found
    def get_rfc(self, rfc_name: str) -> Boolean:
        rfc_owners = self.find_peers_with_rfc(rfc_name)
        if len(rfc_owners) == 0:
            return False
        for (host, port) in rfc_owners.items():
            if self.request_rfc(rfc_name, host, port):
                return True
        return True
