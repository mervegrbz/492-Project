

"""
type=PACKET_IN, buffer_id=0x1, total_len=98, reason=NO_MATCH, table_id=0, cookie=0x0,
match=in_port=1,eth_src=00:0a:95:9d:68:16,eth_dst=00:0a:95:9d:68:17,eth_type=0800,ipv4_src=192.168.1.1,ipv4_dst=192.168.1.2
data=<first 128 bytes of packet data>

type=FLOW_REMOVED, cookie=0x2, priority=100, reason=IDLE_TIMEOUT, table_id=0,
duration_sec=300, duration_nsec=0, idle_timeout=60, hard_timeout=0,
packet_count=10, byte_count=1024,
match=in_port=1,eth_src=00:0a:95:9d:68:16,eth_dst=00:0a:95:9d:68:17,eth_type=0800,ipv4_src=192.168.1.1,ipv4_dst=192.168.1.2
"""

# Initialization:
def initialization_algortihm():
    flow_count = get.request(aggregateflow).flow_count
    previous_flow_occupancy_rates = deque(maxlen=20)
    max_flow_count = get.request(stats).n_tables *  get.request(stats).capabilities
    storing_flows = []
    malicious_flows = []


# Prediction Algorithm:
def prediction_algorithm():
    while (True):
        if (message == FLOW_REMOVED):
            flow_count -= 1
        if (message == PACKET_IN):
            flow_count += 1
            storing_flows.append(Flow(params))
            if (check_flow_threshold()):
                detection_algorithm()
        while (True):
            if (high_rate_attack_prediction(flow_count/max_flow_count)):
                detection_algorithm()
            delay(10)


def check_flow_threshold(flow_count: Int):
    if flow_count >= 0.8 * max_flow_count:
       return True
    else:
        return False

def high_rate_attack_prediction(occupancy_rate: Double):
    previous_flow_occupancy_rates.append(occupancy_rate)
    if len(previous_flow_occupancy_rates) > 2:
        flow_rates_difference = previous_flow_occupancy_rates[-1] - previous_flow_occupancy_rates[-2]
        if (flow_difference >= 10) # if difference >= %10
            return True
    return False

def detection_algorithm():
    mean_time, variation_time = calc_time()
    bytes, packets = calc_bytes_packet_counts()
    if (ml_detection_algorithm(mean_time, variation_time, bytes, packets, flow_count))
        mitigation_algorithm()

    
def calc_time():
   flows = get.request(table_stats)()
   mean = 0
   times = []
   for flow in flows:
       times.append(time-flow.time())
    
   return mean(times), stdev(times)

def calc_bytes_packet_counts():
   stats = get.request(aggregateflow)()
   return stats.bytes, stats.packets
   

def mitigation_algorithm():
    get_malicious_flows()
    match_remaining_pck()
    ent_port = calculate_entrophy_ports()
    ent_ip =  calculate_entrophy_ips()
    ent_mac = calculate_entrophy_macs()
    mean_pack_size = get.request(aggregateflow).byte/get.request(aggregateflow).packet
    mean_byte_time = get_mean_byte_time()
    if (ml_mitigation_algorithm(mean_pack_size, mean_byte_time, ent_port, ent_ip, ent_mac)):
        black_list = crate_blacklist()
        block(black_list)

def get_malicious_flows():
    for i in range(1,254):
        table_flows = get.request(stats/flow/i)
        for flow in table_flows:
            byte_per_packet = flow.byte / flow.packet
            if (byte_per_packet < threshold): # elephant flows couldn't enter here because they have much more higher b_p
                malicious_flows.append(table_flows)

def get_mean_byte_time():
    lst = []
    for i in range(1,254):
        table_flows = get.request(stats/flow/i)
        for flow in table_flows:
            lst.append(flow.byte / flow.duration_time)
    return lst.mean



"""It matches the remaining packets in the table by comparing DB that we adds 
flows with some characteristic features (time, dst_src, dst_port, dst_mac, src_src, src_port, src_mac)
in each packet_in message and the get flow stats by matching them w.r.t features"""

def match_remaining_pck():
     stats = get_flow_stats()
###### Understand that this flow is removed with flow_removed before
     for flow in storing_flows:
          if not flow in stats: 
               DB.delete(flow) 
     for index in range(len(DB)):
        ###### Understand the same flow is append again in the future, we pick the only lastly appended flow
        if  (DB[index] in DB[index+1:]): 
            DB.delete(index)
"""The same flow may removed with flow_removed then added 
packet_in again. To illustrate this, the older flows should be deleted from DB to calculate time correctly,
need to be careful about iterators because we delete some objects
"""

    


