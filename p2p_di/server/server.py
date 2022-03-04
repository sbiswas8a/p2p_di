from threading import *
from math import inf
from threading import Thread
import time
import socket
from p2p_di.server.rs import RegistrationServer
from p2p_di.utils.message import Message, MessageType, StatusCodes

# General Server class


class Server():

    # constructor
    def __init__(self) -> None:
        self.host = socket.gethostbyname(socket.gethostname()+".local")
        self.running = False

    # function to process new connections in separate threads
    # overridden in child classes
    def process_new_connection(client_socket, client_address) -> None:
        pass

    # starts listening
    # @param port to listen on
    # @param period is how long to run server for. Default is infinite
    def startup(self, port, period=inf) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.host, port)
        # Allow 10 connections to queue before dropping new requests
        self.listen(10)
        self.running = True
        self.start_time = time.time()
        print("Ready to connect on: " + self.host + ":" + port)

        while self.running and time.time() < self.start_time + period:
            client_socket, client_address = self.socket.accept()
            new_thread = Thread(target=self.process_new_connection, args=(
                client_socket, client_address), daemon=True)
            new_thread.start()

    def create_error_response(self, e: Exception, code: StatusCodes) -> Message:
        type: MessageType = None
        if isinstance(self, RegistrationServer):
            type = MessageType.SERVER_RESPONSE
        else:
            type = MessageType.PEER_RESPONSE
        response = Message(type)
        response.headers['hostname'] = self.host
        response.status_code = code.value
        response.data = str(e)
        return response

    # stop the server
    def stop(self):
        self.socket.close()
        self.running = False
