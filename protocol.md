## Sequential Consistency
There are several ways to achieve sequential consistency, such as remote-write(primary-based), local read algorithm and local write algorithm. We choose the local read protocol because it is the simplest one (mainly because no need for a mater replica), even though it is not the most write-efficient one.

Each replica process P run the following algorithm:
- Upon `read(x)`: generate `ok(v)` where `v` is the value of `x` in the local replica (local read);
- Upon `write(x, v)`: totally ordered broadcast `write(x, v)` to all replicas;
- Upon receiving totally-ordered-broadcast `write(x, v)` from Q: 
    - set local value of `x` to `v`;
    - if P=Q, generate `ok` for `write(x, v)`.


## Linearizability
Linearizability is a stronger consistency model than sequential consistency. So we need to modify the local read protocol to achieve linearizability. In this case, all operations (including reads) require a totally ordered broadcast.

## Eventual Consistency
Once a server receives a write request, it will update its local state and then propagate the write request to all other servers. The broadcast message will be delivered with a timestamp.

Each server will need to record the timestamp of the last message it received. We maintain a dictionary, the key will be the key value, and the value will be largest modification information they have ever seen. To break the tie, we use the tuple `(timestamp, server_id, value)`.

Once a server receive a broadcast message:
- if the timestamp of the message is greater than the timestamp of the last message it received:
    - update the local state;
    - update the timestamp of the last message it received.
- if the timestamp of the message is less than or equal to the timestamp of the last message it received:
    - ignore the message.

Since each server will broadcast the received "set" messages to *all* servers, the message will eventually be delivered to all servers, **including itself**. So if its own lamport clock is the largest, it will also know at some point. Therefore, eventual consistency is achieved.