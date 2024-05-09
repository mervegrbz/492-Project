# this class will process the data coming from history batches and will detect the anomalies

import numpy as np
import pandas as pd

HIGH_RATE_THRESHOLD = 20 ## it is a threshold value for detecting high rate attack
HIGH_RATE_FLAG = False
LOW_RATE_FLAG = False

def get_occupancy_rate(self, data):
    ## data is a type of pd.DataFrame 
    ## check the occupancy rate if it is higher than 0.8 then general attack can be occured
    capacity_derivatives = data['capacity_used'].diff()
    capacity_last_row = data['capacity_used'].iloc[-1]
    
    if (capacity_last_row > 0.8):
        print("General Attack Detected")
        return True
    ## check the occupancy derivatives trend if the trend is increased immediately then it can be a high rate attack
    ## if the trend is increased gradually then it can be a low rate attack
    ##  get the mean of the  derivatives and check the last derivative is higher than the mean
    ## if it is higher than the mean then it can be a high rate attack
    mean_capacity_derivatives = capacity_derivatives.mean()
    last_capacity_derivative = capacity_derivatives.iloc[-1]
    if (last_capacity_derivative > mean_capacity_derivatives):
        print("High Rate Attack Detected")
        return True
    
def get_packet_in_rate(self, data):
    ## check the packet in rate if it is higher than 20 then it can be a high rate attack
    packet_in_rate = data['packet_in_rate'].diff()
    packet_in_rate_last_row = data['packet_in_rate'].iloc[-1]
    if (packet_in_rate_last_row > HIGH_RATE_THRESHOLD):
        print("High Rate Attack Detected")
        return True
    ## low rate attacks generally have low differences between the packet in rates if the packet in change rate is too regular then it can be a low rate attack
    ## check the entropy of the packet in rate
    entropy = self.get_entropy(packet_in_rate)
    if (entropy < 0.1):
        print("Low Rate Attack Detected")
        return True

def get_entropy(self, data):
    unique, counts = np.unique(data, return_counts=True)
    probabilities = counts / len(data)
    entropy = -np.sum(probabilities * np.log2(probabilities))
    return entropy

def get_flow_table_stats(self, data):
    columns = ['timestamp', 'capacity_used', 'removed_flow_average_duration', 'removed_flow_byte_per_packet', 'average_flow_duration_on_table', 'packet_in_mean', 'packet_in_std_dev']
    ## get the last 5 data row and get their average _flow duration on table and removed flow average duration if average flow duration is increasing then  it can be low rate attack
    ## if removed flow average duration and the average flow duration has a big difference then it can be a low rate attack
    average_flow_duration_on_table = data['flow_duration_on_table'].iloc[-5:]
    mean_removed = data['removed_flow_average_duration'].mean()
    average_flow_duration_on_table_last_row = average_flow_duration_on_table.iloc[-1]
    ## if the average flow duration is bigger then idle timeout and mean removed is bigger than then the now average flow duration then it can be a low rate attack
    if (average_flow_duration_on_table_last_row > 10 and  mean_removed - average_flow_duration_on_table_last_row > 5):
        print("Low Rate Attack Detected")
        return True

def flow_mod_statistics(self, data):
    ## we can find the 5 tuple by using the flows that we have in the flow table
    print("Flow Mod Statistics")
    print(data)
    

        
        
        
        
        
        
        
        
          
      
