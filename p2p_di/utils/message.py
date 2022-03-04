from enum import Enum
from sre_constants import SUCCESS
from typing import Any


class MessageType(Enum):

    REQUEST_SERVER = 1
    REQUEST_PEER = 2
    SERVER_RESPONSE = 3
    PEER_RESPONSE = 4


class MethodType(Enum):

    # peer to RS
    REGISTER = 1
    LEAVE = 2
    KEEP_ALIVE = 3
    PQUERY = 4

    # p2p
    RFC_QUERY = 5
    GET_RFC = 6


class StatusCodes(Enum):

    SUCCESS = 200
    BAD_REQUEST = 400
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500

# Class for messages across clients and servers


class Message():

    CRLF = '<crlf>'

    def __init__(self, type: MessageType) -> None:
        self.headers = {}
        self.message_type = type.name
        self.method = ''
        self.data: Any = None
        if type.name.__contains__('RESPONSE'):
            self.status_code = ''

    def __str__(self):
        string = ''
        #
        string += self.CRLF.join(["'{}':'{}'".format(k, v)
                                 for k, v in self.headers.items()])
        string += self.CRLF
        #
        string += "'message_type':'{}'".format(self.message_type)
        if self.method:
            string += "{}'method':'{}'".format(self.CRLF, self.method)
        if self.status_code:
            string += "{}'status_code':'{}'".format(
                self.CRLF, self.status_code)
        if self.data:
            string += "{}'data':'{}'".format(self.CRLF, self.data)
        return string

    def to_bytes(self):
        return bytes(str(self), 'utf-8')

    @staticmethod
    def string_to_dict(string: str) -> dict:
        tokens = string.split(Message.CRLF)
        dict_string = '{'
        dict_string += ','.join(tokens)
        dict_string += '}'
        return eval(dict_string)

    @staticmethod
    def bytes_to_dict(bytes: bytes) -> dict:
        string = bytes.decode('utf-8')
        return Message.string_to_dict(string)
