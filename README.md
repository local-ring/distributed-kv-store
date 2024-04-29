# Distributed Multi-Consistency Key-Value Store

Here we implement distributed key-value store server with different consistency levels. The consistency schemes we implement are:
- sequential consistency
- eventual consistency
- linearizability

## Repository Structure
- `server.py`: the server class that implements the key-value store server
- `client.py`: the client class that implements the client that sends requests to the server
- `main.py`: the main file that initiates the cluster and clients
- `test/`: the directory that contains test configuration files
- `protocol.md`: the document that describes the protocol of the key-value store server


## Test Cases
Before testing, we need to make sure that `ZeroMQ` is installed. If not, install it by running:
```bash
pip install pyzmq
```

For testing, we *don't* need to run the server and client separately. 

In the `main.py` file, it will initiate the cluster with several servers *as different independent processes*. Then it will initiate several clients to send requests to the servers using different process. All necessary starting information need to be contained in a test configuation file. 

The test configuration file is a json file. The format of the test configuration file is as follows:
```json
{
    "num_servers": 1,
    "consistency_level": "sequential",
    "port_number": {"0": [3000, 3001, 3002]},
    "clients": [
                {"client_number": 1, 
                "requests": [{"request_type": "write", "key": "key1", "value": "value1"}], 
                "server_number": 0}
    ]
}
```


Thus, to run the test, we can run the following command:

```bash
python main.py test_config_path
```
where `test_config_path` is the path to the test configuration file. For example, we can run the following command:
```bash
python main.py test/t1-1.json
```
In the test directory, we have several test configuration files.
- `t1-1.json`: performance test for linearizability consistency
- `t1-2.json`: performance test for sequential consistency
- `t1-3.json`: performance test for eventual consistency
- `t2.json`: test linearizability consistency
- `t3.json`: test sequential consistency
- `t4.json`: test eventual consistency

The first three tese cases are performance tests, it have exact the same requests but with different consistency levels so that we can compare the performance of different consistency levels. The last three test cases are correctness tests for different consistency levels to see if they can achieve the desired consistency level.

## Test Results
### Correctness Test
#### Linearizability
We have the follwing output for the linearizability test (more test can be seen in the performance test section):
![](/img/t2.png)

To verify the correctness of the implementation, we need to see that there is a unique history of sequence of operations that is consistent with the real-time order of operations. In the test case, we can see that client 0 sent the request of set first, and then client 1 sent the request of set. Then client 0 sent the request of get, and finally client 1 sent the request of get. The return value of the get request of client 1 should be the value that client 0 set. We can see that the return value of the get request of client 1 is the value that client 0 set, which means that the implementation achieves linearizability.

Similar verification can be found in the test case from performance test section.

#### Sequential Consistency
To verify the correctness of the implementation, we use the example in the test book (M. van Steen and A.S. Tanenbaum, Distributed Systems, 4th ed., distributed-systems.net, 2023. p. 397): 

![test book](/img/sequential.png)

For the first two servers, it will execute the request to set value of `a` to differenct values. The initial value of `a` is 0. The last two servers will execute the request to get the value of `a` *twice*. To achieve sequential consistency, the order of return value of the two get requests should be the same for both last two servers. 

We have the follwing output for the sequential consistency test, including serveral runs since the test is non-deterministic due to the random delay we introduce in the client side:
Experiment 1            | Experiment 2             | Experiment 3         
:-------------------------:|:-------------------------: |:-------------------------:
![1](/img/t3-1.png) | ![2](/img/t3-2.png) | ![3](/img/t3-3.png)

We can see that no matter how many times we run the test, the order of the return value of the two get requests is always the same for both last two servers, which means that the implementation achieves sequential consistency.

#### Eventual Consistency

To verify the correctness of the implementation, we need to see if all servers have the same value for the same key after some time. For test case, we have 4 servers and 4 clients. Each client will send a set request to set the value of `a` to a different value. Then it will send multiple get requests to get the value of `a` so that we can see if the value of `a` is eventually consistent across all servers.

We have the follwing output for the eventual consistency test (the output is too long to be included in one image, so we split it into two parts):
Part 1          | Part 2            | 
:-------------------------:|:-------------------------: 
![1](/img/t4-1.png) | ![2](/img/t4-2.png) 

We can see that eventually, all servers have the same value (`400`) for the key (`a`), which means that the implementation achieves eventual consistency.

### Performance Test
After verifying the correctness of the implementation, we test the performance of the different consistency levels. For each consistency level, we test the same scenario with three servers and three clients, each client will send 1 set request and 1 get request. The test results are as follows:
#### Linearizability
![](/img/t1-1.png)
#### Sequential Consistency
![](/img/t1-2.png)
#### Eventual Consistency
![](/img/t1-3.png)

We can see that the result is as expected, linearizability is the slowest (around 4 seconds on average), sequential consistency (around 0.05 second on average) is faster than linearizability but slower than eventual consistency, and eventual consistency is the fastest (around 0.002 second on average).


## Design Details

## Communication Framework
We use `ZeroMQ` to implement the communication framework. 

We use the `REQ-REP` pattern to implement the communication between the client and the server. The client will send a request to the server, and the server will send a response back to the client. The request will be in the format of `json` (e.g. `{"type": "get", "key": "a", "value": 10}`) and the response will be in the format of `string`.

Since we want to test the performance with all conditions being the same except consistency (so that for performance test, we can manually avoid any random delay), we introduce a random delay in the client side as a request, that is, when it receives a message `{"type": "sleep"}`, it will trigger a random time delay before sending the next request. The random delay is between 0 and 1 second.

For totally ordered broadcast, we use the `PUB-SUB` pattern. The server will publish the message to all servers, and all other servers will subscribe to the message. 

When initiating the cluster, we will start several servers as different independent processes. Each server will have a unique id and a unique port number. The server will bind to it `PUB` socket and `REP` socket. The client will connect to the `REP` socket of the server. Meanwhile, the server will connect to the `PUB` socket of all other servers.

The message will be in the format of `json`, for example:
```{json}
{"timestamp": 1, "id": 0, "type": "get", "key": "a", "value": 10, "ack": 0}
```
The `ack` is for server handler to distinguish the message type, the broadcast of original message or acknowledgement. The `timestamp` is the lamport clock of the server that sends the message. The `id` is the id of the server that sends the message. The `type` is the type of the message (e.g. `get`, `set`).

You may notice that the test configuration file assign three port numbers to each server, but according to what I just said, we only need two ports for each server, one for `REP` socket and one for `PUB` socket. The reason is that I tried to use the `ROUTER-DEALER` pattern to implement the communication between the servers, one port for `ROUTER` socket (listening) and one port for `DEALER` socket (sending). 

The reason why I intially chose this is `ROUTER` socket can handle multiple connections and track the identity of the sender. However, I found it always receive the same message twice even though the message is only sent once. I tried to debug it for a long time but I couldn't find the reason. So I switch to `PUB-SUB` pattern for the broadcast and I include the sender's id `id` in the message.

## Sequential Consistency
There are several ways to achieve sequential consistency, such as remote-write(primary-based), local read algorithm and local write algorithm. We choose the local read protocol (mentioned in the lecture slides) because it is the simplest one (mainly because no need for a mater replica), even though it is not the most write-efficient one.

Each replica process P run the following algorithm:
- Upon `read(x)`: generate `ok(v)` where `v` is the value of `x` in the local replica (local read);
- Upon `write(x, v)`: totally ordered broadcast `write(x, v)` to all replicas;
- Upon receiving totally-ordered-broadcast `write(x, v)` from Q: 
    - set local value of `x` to `v`;
    - if P=Q, generate `ok` for `write(x, v)`.

For the implementaion of totally ordered broadcast, we use the same algorithm I designed in the second assignment. The only differen is, during execution of write request (that is, when it is popped up by the queue handler), we will lock the key-value store. But when we receive a get request, we don't need to lock the key-value store.

## Linearizability
Linearizability is a stronger consistency model than sequential consistency. So we need to modify the local read protocol to achieve linearizability. In this case, all operations (including reads) require a totally ordered broadcast.

## Eventual Consistency
Once a server receives a write request, it will update its local state and then propagate the write request to all other servers. The broadcast message will be delivered with a timestamp.

Each server will need to record the timestamp of the last message it received. We maintain a dictionary, the key will be the key value, and the value will be largest modification information they have ever seen. To break the potential tie, we use the tuple `(timestamp, server_id, value)`, so that if two messages have the same timestamp, we can break the tie by comparing the server id and the value. Note that the combination of these three will always be unique.

Once a server receive a broadcast message:
- if the timestamp of the message is greater than the timestamp of the last message it received:
    - update the local state;
    - update the timestamp of the last message it received.
- if the timestamp of the message is less than or equal to the timestamp of the last message it received:
    - ignore the message.

Since each server will broadcast the received "set" messages to *all* servers, the message will eventually be delivered to all servers, **including itself**. So if its own lamport clock is the largest, it will also know at some point. Therefore, eventual consistency is achieved.



## Future Work
- Implement more consistency levels: causal consistency, continuous consistency, etc.
- Use Paxos to implement the consensus algorithm for pick leader for the current operation for the whole store
- Achieve lock-free; some primary-based implementation
- Dynamic port number allocation