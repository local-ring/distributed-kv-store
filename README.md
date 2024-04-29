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

#### Sequential Consistency
We have the follwing output for the sequential consistency test, including serveral runs since the test is non-deterministic due to the random delay we introduce in the client side:
Experiment 1            | Experiment 2             | Experiment 3         
:-------------------------:|:-------------------------: |:-------------------------:
![1](/img/t3-1.png) | ![2](/img/t3-2.png) | ![3](/img/t3-3.png)
#### Eventual Consistency

### Performance Test
