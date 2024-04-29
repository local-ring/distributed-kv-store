import zmq
import sys
import json
import time
import threading
from collections import defaultdict
import heapq

class Server:
    """
    This class represents a server in the cluster. It is responsible for handling the requests from the clients and other servers.
    It will handle the following requests from the clients:
    - set(key, value)
    - get(key)

    It will handle the following requests from the other servers: # TODO: this is the critical part
    - update(key, value)
    """
    def __init__(self, server_number, port_number, contacts):
        """
        The server need to initialize the key-value store and the sockets for sending and receiving messages.
        The contacts contains port numbers of the other servers in the cluster.
        """
        self.kv_store = defaultdict(int)
        self.kv_store_lock = threading.Lock()

        self.server_number = server_number
        self.recv_port, self.send_port, self.api_port = port_number

        self.contacts = contacts

        self.context = zmq.Context()
        self.recv_socket = self.context.socket(zmq.ROUTER) # to receive messages from the other servers
        self.recv_socket.bind(f"tcp://*:{self.recv_port}")
        print(f"Server {self.server_number} is ready to receive the messages")

        self.api_socket = self.context.socket(zmq.REP) # to communicate with the clients
        self.api_socket.bind(f"tcp://*:{self.api_port}")
        print(f"Server {self.server_number} is ready to receive the requests from the clients")

        self.send_socket = self.context.socket(zmq.DEALER) # to send messages to the other servers
        self.send_socket.setsockopt(zmq.IDENTITY, str(self.server_number).encode())
        for contact in self.contacts:
            recv_port = self.contacts[contact][0]
            while 1: # the server may not be ready to receive the messages
                try:
                    self.send_socket.connect(f"tcp://localhost:{recv_port}")
                    print(f"Server {self.server_number} is connected to the server {contact}")
                    break
                except zmq.error.ZMQError:
                    time.sleep(1)

        self.poller = zmq.Poller()
        self.poller.register(self.recv_socket, zmq.POLLIN)
        self.poller.register(self.api_socket, zmq.POLLIN)
        self.poller.register(self.send_socket, zmq.POLLIN)


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

        self.acks = {} # to store number of the acknowledgements 
        self.acks_lock = threading.Lock()

        self.total_servers = len(self.contacts)


        self.recv_thread = threading.Thread(target=self._server_handler)
        self.recv_thread.start()

        self.api_thread = threading.Thread(target=self._client_handler)
        self.api_thread.start()


        self.queue_thread = threading.Thread(target=self._queue_handler)
        self.queue_thread.start()



    def _update_clock(self, timestamp=0): # if no timestamp is given, then it is a local event, just increment the clock
        with self.lamport_clock_lock:
            self.lamport_clock = max(self.lamport_clock, timestamp) + 1

    def _broadcast(self, message):
        for contact in self.contacts:
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
                                self.kv_store[key] = value
                                self.api_socket.send_json({"status": "success"})
                            elif operation == "get":
                                self.api_socket.send_json({"status": "success", "value": self.kv_store[key]})
                       

    def _client_handler(self):
        """
        This method is responsible for handling the requests from the clients.
        """
        while 1:
            socks = dict(self.poller.poll())
            if self.api_socket in socks:
                message = self.api_socket.recv_json()
                print(f"Server {self.server_number} received message: {message}")
                self._update_clock()
                broadcast_message = {"timestamp": self.lamport_clock,
                                        "operation": message["type"],
                                        "key": message["key"],
                                        "value": message.get("value"),
                                        "ack": 0}
                self._broadcast(broadcast_message)

    def _server_handler(self):
        """
        This method is responsible for handling the requests from the other servers.
        """
        while 1:
            socks = dict(self.poller.poll())
            if self.recv_socket in socks:
                id, message = self.recv_socket.recv_multipart()
                id = int(id.decode())
                message = json.loads(message.decode())
                self._update_clock(message["timestamp"])
                if message["ack"] == 1:
                    with self.acks_lock:
                        self.acks[(message["timestamp"], message["id"], message["operation"], message["key"], message["value"])] += 1
                else:
                    with self.queue_lock:
                        heapq.heappush(self.queue, (message["timestamp"], 
                                                    id, 
                                                    message["operation"], 
                                                    message["key"], 
                                                    message["value"]))
                    self._update_clock()
                    ack_message = {"timestamp": self.lamport_clock, 
                                    "id": id,
                                    "operation": message["operation"],
                                    "key": message["key"],
                                    "value": message["value"],
                                    "ack": 1}
                    self._broadcast(ack_message)
                    
                
    
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
                                   port_number,
                                   contacts=port_number)
    elif consistency_level == "eventual":
        server = Server_eventual(server_number, 
                                 port_number,
                                 contacts=port_number)
    elif consistency_level == "causal":
        server = Server_causal(server_number, 
                               port_number,
                               contacts=port_number)

