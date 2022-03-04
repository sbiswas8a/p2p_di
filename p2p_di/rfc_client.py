from shutil import copyfile
from math import inf
import os
from __future__ import annotations
from random import randint
import socket
from typing import Dict, List
from p2p_di.server.rfc_server import RFC_Server
from p2p_di.utils.message import Message, MessageType, MethodType, StatusCodes
from p2p_di.utils.utils import DEFAULT_TTL, DEFAULT_UPDATE_INTERVAL, Peer_Entry, BadFormatException, NotRegisteredException, get_rs_address, log, send, receive, find_free_port

#class for the entries in RFC_Index
class Index_Entry():

    def __init__(self, title:str, owned:bool=False, hosted_on:dict = {}) -> None:
        self.title = title
        self.owned = owned
        # in the form {'ip':port}
        self.hosted_on : Dict[str] = hosted_on

    def is_owned(self) -> bool:
        return self.owned

    def get_peers_who_own(self) -> Dict[str]:
        return self.hosted_on

    def merge_peer_list(self, other:dict) -> None:
        self.hosted_on | other


class RFC_Index():

    def __init__(self, entries: dict = {}) -> None:
        self.rfc_store : str = None
        self.rfcs : Dict[str,Index_Entry] = entries

    def __str__(self) -> str:
        return str(self.rfcs)

    def is_owned(self, rfc:str):
        return rfc in self.rfcs and self.rfcs[rfc].is_owned()

    def get_owners(self, rfc:str) -> Dict[str]:
        if rfc not in self.rfcs:
            return {}
        else:
            return self.rfcs[rfc].get_peers_who_own()
    
    def to_bytes(self) -> bytes:
        return bytes(str(self), 'utf-8')

    def merge_index(self, other:RFC_Index):
        for rfc in other.rfcs:
            if rfc not in self.rfcs:
                self.rfcs[rfc] = other.rfcs[rfc]
            else:
                self.rfcs[rfc] | other.rfcs[rfc]
    
    @staticmethod
    def from_bytes(bytes: bytes) -> RFC_Index:
        string = bytes.decode('utf-8')
        rfc_list = eval(string)
        to_return = RFC_Index()
        to_return.rfcs = rfc_list
        return to_return
        

class Client():

    # name is not hostname
    # @rfcs_owned is filename containing list of rfcs stored locally
    # rfcs_owned must have each rfc owned on a separate line
    def __init__(self, name:str, rfcs_owned_list:str=None, port:int=None) -> None:
        random_int = randint(0,999)
        self.name = '{}_{}'.format(name, random_int)
        self.cookie : str = None
        self.peer_list: Dict[str, str] = {}
        base_path = os.path.dirname(__file__)
        self.log_filename = os.path.join(base_path, '..', 'assets', 'peer', self.name, 'action_log.txt')
        if rfcs_owned_list:
            rfcs_owned_list = os.path.join(os.getcwd(), rfcs_owned_list)
            self.rfc_index : RFC_Index = self.load_rfcs(rfcs_owned_list)
        else:
            self.rfc_index : RFC_Index = RFC_Index()
        self.rfc_index.rfc_store = os.path.join(base_path, '..', 'assets', 'peer', self.name, 'rfc_store')
        self.rfc_server = RFC_Server(self.name, self.rfc_index, True, port)

    # load rfc
    def load_rfcs(self, filename: str) -> RFC_Index:
        owned = RFC_Index()
        base_path = os.path.dirname(__file__)
        if not os.path.isfile(filename):
            owned
        with open(filename) as file:
            while line := file.readline().strip():
                file_path = os.path.join(base_path, '..', 'rfc_store', line)
                if os.path.isfile(file_path):
                    copyfile(file_path, os.path.join(base_path, '..', 'assets', 'peer', self.name, 'rfc_store', file_path))
                    owned.rfcs[filename] = Index_Entry(filename, True)
        return owned

    def register(self):
        log(self.log_filename, 'Attempting to register on server', type='info')
        self.cookie = self.rfc_server.register(self.name)
    
    def stay_alive(self):
        log(self.log_filename, 'Pinging server to stay alive', type='info')
        self.rfc_server.server_requester(self.cookie, MethodType.KEEP_ALIVE, {'success':'Successfully pinged server!', 'failure':'Failed to ping server'})
    
    def query_for_peers(self):
        log(self.log_filename, 'Querying server for peers', type='info')
        peer_strings : List[str] = self.rfc_server.server_requester(self.cookie, MethodType.PQUERY, {'success':'Received peer list from server!'})
        for string in peer_strings:
            address = string.split(':')
            self.peer_list[address[0]] = address[1]
    
    def leave_rs(self):
        log(self.log_filename, 'Leaving server', type='info')
        self.rfc_server.server_requester(self.cookie, MethodType.LEAVE, {'success':'Successfully updated status!', 'failure':'Failed to update status'})