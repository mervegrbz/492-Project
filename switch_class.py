
import time

class Switch:
    
    flow_table = []
    connection_time = 0
    datapath_id = 0
    n_buffers = 0
    n_tables = 0
    n_packet_in = 0
    n_flow_removed = 0
    flow_mods = 0
    capacity = 0
    capabilities = 0
    flow_removed = []
    idle_timeout = 0
    


    def __init__(self, connection_time, datapath_id, n_buffers, n_tables, capabilities):
        self.connection_time = connection_time
        self.datapath_id = datapath_id
        self.n_buffers = n_buffers
        self.n_tables = n_tables
        self.capabilities = capabilities

    def calc_flow_stats(self):
        ## todo resaon should be add
        used_capacity = self.flow_mods - self.n_flow_removed
        if((used_capacity / self.capacity)>0.8):
            print("Switch %s is overloaded" % self.datapath_id)
    
    
    def calc_removed_flows(self):
        average_duration = 0
        average_byte_per_packet = 0
        # TODO get the last N elements of the removed flows to monitor change
        for i in self.flow_removed:
            duration_sec = i.duration_sec
            reason = i.reason
            byte_count = i.byte_count
            packet_count = i.packet_count
            idle_timeout = i.idle_timeout
            average_byte_per_packet += byte_count/packet_count
            average_duration += duration_sec
        self.flow_average_duration = average_duration/len(self.flow_removed)
        self.flow_average_byte_per_packet = average_byte_per_packet/len(self.flow_removed)
    def match_packet_in_removed(self):
       
        for i in self.flow_removed:
            duration_sec = i.duration_sec
            timestamp = i.timestamp
            packet_in_ts = timestamp - duration_sec *1000
            for j in self.flow_table:
                if j.timestamp == packet_in_ts:
                    self.flow_table.remove(j)
            

    def inspect_flow_table(self):
        total_duration = 0
        for i in self.flow_table:
            now = time.time()
            total_duration += now - i.timestamp
        average_duration = total_duration/len(self.flow_table)
        print("Average duration of flows in flow table is %s" % average_duration)
        return average_duration

    def __str__(self):
        return self.state
                
                
                
                
                
            
            
        
        
        
        
        
         
            
            
            
            
            
            
            
