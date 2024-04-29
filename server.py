import zmq
import sys
import json
import time
import threading
from collections import defaultdict
import heapq


HEARTBEAT = {"ping": "pong"}

class Server:
    """
    This class represents a server in the cluster. It is responsible for handling the requests from the clients and other servers.
    It will handle the following requests from the clients:
    - set(key, value)
    - get(key)

    It will handle the following message from the other servers:
    - broadcast message
    - broadcast acknoledgement
    """
    def __init__(self, server_number, port_number, contacts):
        """
        The server need to initialize the key-value store and the sockets for sending and receiving messages.
        The contacts contains port numbers of the other servers in the cluster.
        """
        # self.kv_store = defaultdict(int)
        self.kv_store = {"a": 0, "b": 0}
        self.kv_store_lock = threading.Lock()

        self.server_number = int(server_number)
        self.recv_port, self.send_port, self.api_port = port_number

        self.contacts = contacts

        self.context = zmq.Context()

        self.send_socket = self.context.socket(zmq.PUB) # to send messages to the other servers
        self.send_socket.bind(f"tcp://*:{self.send_port}")
        # threading.Thread(target=self._daemon).start()

        self.api_socket = self.context.socket(zmq.REP) # to communicate with the clients
        self.api_socket.bind(f"tcp://*:{self.api_port}")
        print(f"Server {self.server_number} is ready to receive the requests from the clients")

        self.recv_socket = self.context.socket(zmq.SUB) # to receive messages from the other servers
        for contact in self.contacts:
            recv_port = self.contacts[contact][1]
            self.recv_socket.connect(f"tcp://localhost:{recv_port}")
            print(f"Server {self.server_number} is connected to the server {contact}")
        self.recv_socket.setsockopt_string(zmq.SUBSCRIBE, '')

        self.poller = zmq.Poller()
        self.poller.register(self.recv_socket, zmq.POLLIN)
        self.poller.register(self.api_socket, zmq.POLLIN)
        # self.poller.register(self.send_socket, zmq.POLLOUT)

class Server_linearizability(Server):
    """
    This class represents a server in the cluster with linearizability consistency level.
    """
    def __init__(self, server_number, port_number, contacts):
        super().__init__(server_number, port_number, contacts)

        self.lamport_clock = 0
        self.lamport_clock_lock = threading.Lock()

        self.queue = [] # to store the requests
        heapq.heapify(self.queue) # to sort the requests based on the timestamp
        self.queue_lock = threading.Lock()

        self.acks = defaultdict(int) # to store number of the acknowledgements 
        self.acks_lock = threading.Lock()

        self.total_servers = len(self.contacts)

        self.api_thread = threading.Thread(target=self._client_handler)
        self.api_thread.start()

        self.recv_thread = threading.Thread(target=self._server_handler)
        self.recv_thread.start()

        self.queue_thread = threading.Thread(target=self._queue_handler)
        self.queue_thread.start()


    def _update_clock(self, timestamp=0): # if no timestamp is given, then it is a local event, just increment the clock
        with self.lamport_clock_lock:
            self.lamport_clock = max(self.lamport_clock, timestamp) + 1

    def _broadcast(self, message):
        # for contact in self.contacts:
        #     recv_port = self.contacts[contact][0]
        #     self.send_socket.connect(f"tcp://localhost:{recv_port}")
        #     # print(f"Server {self.server_number} is connected to the server {contact}")
        #     self.send_socket.send_json(message)
        #     # print(f"Server {self.server_number} sent message to server {contact}: {message}")
        #     self.send_socket.disconnect(f"tcp://localhost:{recv_port}")

        self.send_socket.send_json(message)


    def _queue_handler(self):
        while 1:
            if self.queue:
                with self.queue_lock:
                    timestamp, id, operation, key, value = self.queue[0]
                    with self.acks_lock:
                        if self.acks[(timestamp, id, operation, key, value)] == self.total_servers:
                            timestamp, id, operation, key, value = heapq.heappop(self.queue)
                            if operation == "set":
                                with self.kv_store_lock:
                                    self.kv_store[key] = value
                                    if id == self.server_number:
                                        self.api_socket.send_string("success")
                                        print(f"Server {self.server_number} set the value of the key {key} to {value}")
                            elif operation == "get":
                                if id == self.server_number:
                                    self.api_socket.send_string(f"{key}:{self.kv_store[key]}")
                                    print(f"Server {self.server_number} got the value of the key {key} as {self.kv_store[key]}")

            # time.sleep(1)
                       
    def _heartbeat(self): # keep api_socket alive
        while 1:
            self.api_socket.send_string("ping")
            response = self.api_socket.recv_string()
            if response == "pong":
                continue
            elif response == "gotcha":
                break

            time.sleep(1)

    def _client_handler(self):
        """
        This method is responsible for handling the requests from the clients.
        """
        while 1:
            socks = dict(self.poller.poll())
            if self.api_socket in socks:
                message = self.api_socket.recv_json()
                # threading.Thread(target=self._heartbeat).start()
                # print(f"Server {self.server_number} received message: {message}")
                self._update_clock()
                broadcast_message = {"timestamp": self.lamport_clock,
                                        "operation": message["type"],
                                        "key": message["key"],
                                        "value": message["value"],
                                        "ack": 0,
                                        "id": self.server_number}
                self._broadcast(broadcast_message)

    def _daemon(self):
        while 1:
            self.send_socket.send_json(HEARTBEAT)
            time.sleep(0.5)

    def _server_handler(self):
        """
        This method is responsible for handling the requests from the other servers.
        """
        while 1:
            # socks = dict(self.poller.poll())
            # if self.recv_socket in socks:
            message = self.recv_socket.recv_json()
            if "ping" in message:
                continue
            # print(message)
            id = message["id"]
            # print(f"Server {self.server_number} received message from Server {id}: {message}")
            self._update_clock(message["timestamp"])
            if message["ack"] == 1: 
                with self.acks_lock:
                    self.acks[(message["msg_timestamp"], message["id"], message["operation"], message["key"], message["value"])] += 1
            else: # id is the one who broadcasted the message
                with self.queue_lock:
                    heapq.heappush(self.queue, (message["timestamp"], 
                                                message["id"], 
                                                message["operation"], 
                                                message["key"], 
                                                message["value"]))
                self._update_clock()
                ack_message = {"timestamp": self.lamport_clock, 
                                "id": message["id"],
                                "operation": message["operation"],
                                "key": message["key"],
                                "value": message["value"],
                                "ack": 1,
                                "msg_timestamp": message["timestamp"]}
                self._broadcast(ack_message)


class Server_sequential(Server):
    """
    This class represents a server in the cluster with sequential consistency level.
    """

    def __init__(self, server_number, port_number, contacts):
        super().__init__(server_number, port_number, contacts)

        self.lamport_clock = 0
        self.lamport_clock_lock = threading.Lock()

        self.queue = [] # to store the requests
        heapq.heapify(self.queue) # to sort the requests based on the timestamp
        self.queue_lock = threading.Lock()

        self.acks = defaultdict(int) # to store number of the acknowledgements 
        self.acks_lock = threading.Lock()

        self.total_servers = len(self.contacts)

        self.api_thread = threading.Thread(target=self._client_handler)
        self.api_thread.start()

        self.recv_thread = threading.Thread(target=self._server_handler)
        self.recv_thread.start()

        self.queue_thread = threading.Thread(target=self._queue_handler)
        self.queue_thread.start()


    def _update_clock(self, timestamp=0): # if no timestamp is given, then it is a local event, just increment the clock
        with self.lamport_clock_lock:
            self.lamport_clock = max(self.lamport_clock, timestamp) + 1

    def _broadcast(self, message):
        self.send_socket.send_json(message)

    def _queue_handler(self):
        while 1:
            if self.queue:
                with self.queue_lock:
                    timestamp, id, operation, key, value = self.queue[0]
                    with self.acks_lock:
                        if self.acks[(timestamp, id, operation, key, value)] == self.total_servers:
                            timestamp, id, operation, key, value = heapq.heappop(self.queue)
                            self.kv_store[key] = value
                            if id == self.server_number:
                                self.api_socket.send_string("success")
                                print(f"Server {self.server_number} set the value of the key {key} to {value}")
                       

    def _client_handler(self):
        """
        This method is responsible for handling the requests from the clients.
        """
        while 1:
            socks = dict(self.poller.poll())
            if self.api_socket in socks:
                message = self.api_socket.recv_json()
                self._update_clock()
                if message["type"] == "get": # local read 
                    self.api_socket.send_string(f"{message['key']}:{self.kv_store[message['key']]}")
                    print(f"Server {self.server_number} got the value of the key {message['key']} as {self.kv_store[message['key']]}")
                else:
                    broadcast_message = {"timestamp": self.lamport_clock,
                                            "operation": message["type"],
                                            "key": message["key"],
                                            "value": message["value"],
                                            "ack": 0,
                                            "id": self.server_number}
                    self._broadcast(broadcast_message)

    def _server_handler(self):
        """
        This method is responsible for handling the requests from the other servers.
        """
        while 1:
            message = self.recv_socket.recv_json()
            id = message["id"]
            # print(f"Server {self.server_number} received message from Server {id}: {message}")
            self._update_clock(message["timestamp"])
            if message["ack"] == 1: 
                with self.acks_lock:
                    self.acks[(message["msg_timestamp"], message["id"], message["operation"], message["key"], message["value"])] += 1
            else: # id is the one who broadcasted the message
                with self.queue_lock:
                    heapq.heappush(self.queue, (message["timestamp"], 
                                                message["id"], 
                                                message["operation"], 
                                                message["key"], 
                                                message["value"]))
                self._update_clock()
                ack_message = {"timestamp": self.lamport_clock, 
                                "id": message["id"],
                                "operation": message["operation"],
                                "key": message["key"],
                                "value": message["value"],
                                "ack": 1,
                                "msg_timestamp": message["timestamp"]}
                self._broadcast(ack_message)


class Server_eventual(Server):
    """
    This class represents a server in the cluster with eventual consistency level.
    """
    def __init__(self, server_number, port_number, contacts):
        super().__init__(server_number, port_number, contacts)

        self.lamport_clock = 0
        self.lamport_clock_lock = threading.Lock()

        self.last_modified = defaultdict(tuple) 
        self.last_modified_lock = threading.Lock()

        self.api_thread = threading.Thread(target=self._client_handler)
        self.api_thread.start()

        self.recv_thread = threading.Thread(target=self._server_handler)
        self.recv_thread.start()


    def _update_clock(self, timestamp=0): # if no timestamp is given, then it is a local event, just increment the clock
        with self.lamport_clock_lock:
            self.lamport_clock = max(self.lamport_clock, timestamp) + 1

    def _broadcast(self, message):
        self.send_socket.send_json(message)        
        self._update_clock()

    def _client_handler(self):
        """
        This method is responsible for handling the requests from the clients.
        """
        while 1:
            socks = dict(self.poller.poll())
            if self.api_socket in socks:
                message = self.api_socket.recv_json()
                # print(f"Server {self.server_number} received message: {message}")
                self._update_clock()
                if message["type"] == "get": # local read 
                    self.api_socket.send_string(f"{message['key']}:{self.kv_store[message['key']]}")
                    print(f"Server {self.server_number} got the value of the key {message['key']} as {self.kv_store[message['key']]}")
                elif message["type"] == "set":
                    with self.kv_store_lock:
                        self.kv_store[message["key"]] = message["value"]
                    self.api_socket.send_string("success")
                    print(f"Server {self.server_number} set the value of the key {message['key']} to {message['value']}")
                    self._update_clock()
                    broadcast_message = {"timestamp": self.lamport_clock,
                                            "operation": message["type"],
                                            "key": message["key"],
                                            "value": message["value"],
                                            "id": self.server_number}
                    self._broadcast(broadcast_message)

    def _server_handler(self):
        """
        This method is responsible for handling the requests from the other servers.
        """
        while 1:
            message = self.recv_socket.recv_json()
            id = message["id"]
            print(f"Server {self.server_number} received message from Server {id}: {message}")
            self._update_clock(message["timestamp"])
            modification = (message["timestamp"], message["id"], message["value"])
            with self.last_modified_lock:
                if self.last_modified[message["key"]] < modification:
                    self.last_modified[message["key"]] = (message["timestamp"], message["value"])
                    with self.kv_store_lock:
                        self.kv_store[message["key"]] = message["value"]


class Server_causal(Server):
    def __init__(self, server_number, port_number, contacts):
        super().__init__(server_number, port_number, contacts)

    # TODO: implement the eventual consistency level
                
    
if __name__ == "__main__":
    server_number, port_number, consistency_level = sys.argv[1:]
    port_number = eval(port_number)
    own_port = port_number[server_number]

    if consistency_level == "linearizability":
        server = Server_linearizability(server_number, 
                                        own_port,
                                        contacts=port_number)
    elif consistency_level == "sequential":
        server = Server_sequential(server_number, 
                                   own_port,
                                   contacts=port_number)
    elif consistency_level == "eventual":
        server = Server_eventual(server_number, 
                                 own_port,
                                 contacts=port_number)
    elif consistency_level == "causal":
        server = Server_causal(server_number, 
                               own_port,
                               contacts=port_number)

