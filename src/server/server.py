from threading import *
from math import inf
from threading import Thread
import time
import tinydb
import socket
import platform
import os

# General Server class
# some module code sourced from examples 
# at http://pymotw.com/2/select/
class Server:
    
    #constructor
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
    def startup(self, port=65243, period=inf) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.host, port)
        self.listen(10) # Allow 10 connections to queue before dropping new requests
        self.running = True
        self.start_time = time.time()
        print("Ready to connect on: " + self.host + ":" + port)


        while self.running and time.time() < self.start_time + period:
            client_socket, client_address = self.socket.accept()
            new_thread = Thread(target=self.process_new_connection, args=(client_socket, client_address), daemon=True)
            new_thread.start()
    
    # stop the server
    def stop(self):
        self.socket.close()
        self.running = False
