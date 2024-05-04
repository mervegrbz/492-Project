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