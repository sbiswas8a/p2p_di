from email.mime import base
from math import inf
import os
from __future__ import annotations
from random import randint
from typing import List
from p2p_di.server.rfc_server import RFC_Server
from p2p_di.utils.message import Message, MessageType, MethodType, StatusCodes
from p2p_di.utils.utils import DEFAULT_TTL, DEFAULT_UPDATE_INTERVAL, Peer_Entry, BadFormatException, NotRegisteredException, log, send, receive, find_free_port

class Index_Entry():

    def __init__(self, title: str, hosted_on = None, ttl = DEFAULT_TTL) -> None:
        self.title = title
        if hosted_on == None:
            hosted_on = 'self'
            ttl = inf
        self.hosted_on = hosted_on
        self.ttl = ttl

    def is_owned(self) -> bool:
        return self.hosted_on == 'self'

    def decrement_ttl(self, interval=DEFAULT_UPDATE_INTERVAL) -> None:
        if self.ttl != 0:
            self.ttl -= interval
            if self.ttl <= 0:
                self.ttl = 0


class RFC_Index():

    def __init__(self, entries: List[Index_Entry] = []) -> None:
        self.list : List[Index_Entry] = entries

    def __str__(self) -> str:
        return str(self.list)
    
    def to_bytes(self) -> bytes:
        return bytes(str(self), 'utf-8')
    
    @staticmethod
    def from_bytes(bytes: bytes) -> RFC_Index:
        string = bytes.decode('utf-8')
        rfc_list = eval(string)
        to_return = RFC_Index()
        to_return.list = rfc_list
        return to_return
        

class Client():

    # name is not hostname
    # @rfcs_owned is filename containing list of rfcs stored locally
    # rfcs_owned must have each rfc owned on a separate line
    def __init__(self, name:str, rfcs_owned:str=None) -> None:
        random_int = randint(0,999)
        self.name = '{}_{}'.format(name, random_int)

        base_path = os.path.dirname(__file__)
        self.rfc_store = os.path.join(base_path, '..', 'assets', 'peer', self.name, 'rfc_store')
        self.log_filename = os.path.join(base_path, '..', 'assets', 'peer', self.name, 'action_log.txt')
        self.rfc_server = RFC_Server(self.name)
        if rfcs_owned == None:
            rfcs_owned = os.path.join(base_path, '..', 'assets', 'peer', self.name, 'rfcs_owned.txt')
        self.rfc_index : RFC_Index = self.load_rfcs(rfcs_owned)

    # load rfc
    def load_rfcs(filename: str) -> RFC_Index:
        base_path = os.path.dirname(__file__)
        if not os.path.isfile(filename):
            return RFC_Index()
        owned = RFC_Index()
        with open(filename) as file:
            while line := file.readline().strip():
                file_path = os.path.join(base_path, '..', 'rfc_store', line)
                if os.path.isfile(file_path):
                    owned.list.append[Index_Entry(line)]
        return owned