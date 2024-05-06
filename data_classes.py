from dataclasses import dataclass

# this is for storing occupancy rate
@dataclass
class OccupancyRate:
    occupancy_rate: float
    time: float

# this is for storing packet_in messages
# we will use them to store the in_port and use flow_id to match with OPFC_ADD
@dataclass
class PacketIn:
    flow_id: int
    in_port: int

# this is for storing number of removed flows
@dataclass
class RemovedCount:
    removed_count: float
    time: float

@dataclass
class FlowMod:
    datapath_id: int
    timestamp: float
    match: dict
    command: int
    flags: int
    idle_timeout: int
    hard_timeout: int
    priority: int
    buffer_id: int
    out_port: int
    cookie: int = 0

@dataclass
class PacketIn:
    datapath_id: int
    timestamp: float
    in_port: int
    reason: str
    eth_src: str
    eth_dst: str

@dataclass
class FlowRemoved:
    datapath_id: int
    timestamp: float
    match: dict #ip_protocol, ipv4 src, dst, type
    idle_timeout: float
    duration_sec: float
    duration_nsec: int
    packet_count: int
    byte_count: int
    reason: str
    cookie: int = 0
    priority: int = 1


