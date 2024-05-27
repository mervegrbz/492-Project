# this class will process the data coming from history batches and will predicts the anomalies

import numpy as np
import pandas as pd
from parameters import *
from scipy.stats import entropy

HIGH_RATE_FLAG = False
LOW_RATE_FLAG = False

# it predicts whether the switch is under a low rate attack
def check_low_rate_attack(data):
    capacity_derivatives = data['capacity_used'][-5:].diff(periods=1)
    # if all of last 5 occupancy rates are increased
    if all(x > 0 for x in capacity_derivatives):
        print("Occupancy Rate is increased consistently in last 5 batches")
        if check_removed_flows(data):
            print("Number of Removed Flows are smaller than the mean in last 5 batches")
            if check_capacity_used_rate(data):
                print("Packet in Rate Entropy is smaller than the normal one in last 5 batches")
                print("There can be low rate attack!!")
                return True
    return check_flow_durations(data)


# it checks whether the latest number of removed flows are smaller than the mean
def check_removed_flows(data):
    removed_flow_counts = data['removed_flows_count'].diff(periods=1) #because it's cumulative, take diff
    mean_removed_flow_count = removed_flow_counts.mean()
    last_removed_counts = removed_flow_counts[-5:]
    return all(x < mean_removed_flow_count for x in last_removed_counts)

# it checks whether a consistency is happened in packet in rates to observe a low rate attack
def check_capacity_used_rate(data):
    capacity_used = data['capacity_used'].diff() # because packet in rate is cumulative take diff at first
    
    general_entropy = get_entropy(capacity_used)
    # if it has more than 10 batch in the history, exclude the last 5 one
    if len(capacity_used) > 10:
        general_entropy = get_entropy(capacity_used[:-5])
    
    latest_capacity_used_entropy = get_entropy(capacity_used[-5:]) # last 5 packet in entropy
    return latest_capacity_used_entropy < general_entropy
       
    
def check_high_rate_attack(data):
    packet_in_rates = data['packet_in_rate'].diff()
    packet_in_rate_last_row = packet_in_rates.iloc[-1]
    if (packet_in_rate_last_row > abs(packet_in_rates.mean() * HIGH_RATE_THRESHOLD)):
        print("High Rate Attack Detected")
        print(packet_in_rates)
        return True
    return False


def get_entropy(data):
    data = data.dropna()
    histogram, _ = np.histogram(data, bins=100)
    return entropy(histogram)

def check_flow_durations(data):    
    mean_removed = data['removed_flow_average_duration'].mean()
    average_flow_duration_on_table_last_row = data['average_flow_duration_on_table'].iloc[-1]
    if (average_flow_duration_on_table_last_row - mean_removed  > DURATION_THRESHOLD and mean_removed > IDLE_TIMEOUT):
        print("Low Rate Attack Detected because of flow durations")
        return True
    return False


# in general attack, if last two batch is more than high rate threshold it triggers high rate attack else low rate
def check_general_attack_is_high_rate(data):
    packet_in_rates = data['packet_in_rate'].diff()
    packet_in_rate_last_two_rows = packet_in_rates.iloc[-1]
    if len(packet_in_rates) > 2:
        packet_in_rate_last_two_rows += packet_in_rates.iloc[-2]
    else:
        return True   
    if (packet_in_rate_last_two_rows > packet_in_rates.mean() * HIGH_RATE_THRESHOLD):
        return True
    return False
        
# it checks whether there is an attack after it takes history batches        
def check_attack(data):
    global LOW_RATE_FLAG, HIGH_RATE_FLAG

    capacity_last_row = data['capacity_used'].iloc[-1]
    if (capacity_last_row > CAPACITY_THRESHOLD):
        if check_general_attack_is_high_rate(data):
            HIGH_RATE_FLAG = True
        else:
            LOW_RATE_FLAG = True

    if (len(data) < 5 ):
        print('There is no enough data check_attack for specific type')
        return
    if check_high_rate_attack(data):
        HIGH_RATE_FLAG = True
    elif check_low_rate_attack(data):
        LOW_RATE_FLAG = True

# old method
def get_occupancy_rate2(data):
    global HIGH_RATE_FLAG, LOW_RATE_FLAG
    ## data is a type of pd.DataFrame 
    ## check the occupancy rate if it is higher than 0.8 then general attack can be occured
    capacity_derivatives = data['capacity_used'][-5:].diff(periods=1)
    capacity_last_row = data['capacity_used'].iloc[-1]

    if (capacity_last_row > CAPACITY_THRESHOLD):
        print("General Attack Detected")
        return True
    ## check the occupancy derivatives trend if the trend is increased immediately then it can be a high rate attack
    ## if the trend is increased gradually then it can be a low rate attack
    ##  get the mean of the  derivatives and check the last derivative is higher than the mean
    ## if it is higher than the mean then it can be a high rate attack
    ## TODO we can add other means as well but in smaller weights
    mean_capacity_derivatives = capacity_derivatives.mean()
    last_capacity_derivative = capacity_derivatives.iloc[-1]
    
    # TODO 1.2 neye göre? az bence stdev'i vs'sine de bakılmalıydı high rate'te baya banlıyoz çünkü
    if (last_capacity_derivative > (mean_capacity_derivatives * 1.2) and mean_capacity_derivatives > 0 ):
        print("High Rate Attack Detected")
        print(mean_capacity_derivatives, capacity_derivatives)
        HIGH_RATE_FLAG = True
        
        return True

# old method
def get_packet_in_rate2(data):
    global HIGH_RATE_FLAG, LOW_RATE_FLAG
    ## check the packet in rate if it is higher than 20 then it can be a high rate attack
    packet_in_rate = data['packet_in_rate'][-5:].diff()
    packet_in_rate_last_row = packet_in_rate.iloc[-1]
    if (packet_in_rate_last_row > abs(packet_in_rate.mean() * HIGH_RATE_THRESHOLD)):
        print("High Rate Attack Detected")
        print(packet_in_rate)
        HIGH_RATE_FLAG = True
        return True
    ## low rate attacks generally have low differences between the packet in rates if the packet in change rate is too regular then it can be a low rate attack
    ## check the entropy of the packet in rate
    entropy = get_entropy(packet_in_rate)
    print(entropy)
    if (entropy < 0.1):
        print("Low Rate Attack Detected because of entropy")
        LOW_RATE_FLAG = True
        return True
        
        
        
          
      
