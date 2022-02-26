from email import header
from enum import Enum


class MessageType(Enum):
    
    REQUEST_SERVER = 1
    REQUEST_PEER = 2
    SERVER_RESPONSE = 3 
    PEER_RESPONSE = 4

# Class for messages across clients and servers
class Message():

    CRLF = '<crlf>'
    SPACE = '<sp>'
    HEADER = '<h>'


    def __init__(self, type : MessageType) -> None:
        self.headers = {}
        self.message_type = type.name
        self.method = ''
        self.data = ''

    def __str__(self):
        string = ''
        #
        string += self.CRLF.join(["'{}':'{}'".format(k, v) for k, v in self.headers.items()])
        string += self.CRLF
        #
        string += "'message_type':'{}'{}".format(self.message_type, self.CRLF) 
        string += "'method':'{}'".format(self.method)
        if self.data:
            string += "{}'data':'{}'".format(self.CRLF, self.data)
        return string

    def to_bytes(self):
        return bytes(str(self), 'utf-8')

    def byte_to_string(self, bytes : bytes) -> str:
        return bytes.decode('utf-8')

    def string_to_dict(self, string: str) -> dict:
        tokens = string.split(self.CRLF)
        dict_string = '{'
        dict_string += ','.join(tokens)
        dict_string += '}'
        return eval(dict_string)