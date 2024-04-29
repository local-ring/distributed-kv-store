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
