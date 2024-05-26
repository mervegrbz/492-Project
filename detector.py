# this class will process the data coming from history batches and will detect the anomalies

import numpy as np
import pandas as pd
from parameters import *
from scipy.stats import zscore

HIGH_RATE_FLAG = False
LOW_RATE_FLAG = False

def get_occupancy_rate(data):
    global HIGH_RATE_FLAG, LOW_RATE_FLAG
    ## data is a type of pd.DataFrame 
    ## check the occupancy rate if it is higher than 0.8 then general attack can be occured
    capacity_derivatives = data['capacity_used'][-5:].diff(periods=1)
    capacity_last_row = data['capacity_used'].iloc[-1]
    ## TODO removed flowlarin sayisi can we used it for detection
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
    
def get_packet_in_rate(data):
    global HIGH_RATE_FLAG, LOW_RATE_FLAG
    ## check the packet in rate if it is higher than 20 then it can be a high rate attack
    packet_in_rate = data['packet_in_rate'][-5:].diff()
    packet_in_rate_last_row = packet_in_rate.iloc[-1]
    if ( packet_in_rate_last_row > abs(packet_in_rate.mean() * HIGH_RATE_THRESHOLD)):
        print("High Rate Attack Detected")
        # TODO bu nasil negatif cikiyor ya
        print(packet_in_rate)
        HIGH_RATE_FLAG = True
        return True
    ## low rate attacks generally have low differences between the packet in rates if the packet in change rate is too regular then it can be a low rate attack
    ## check the entropy of the packet in rate
    ## TODO add this to the occupency rate not packet in
    ## TODO neden capacity'sinin artışına bakmadık da packet in'e baktık?
    entropy = get_entropy(packet_in_rate)
    print(entropy)
    if (entropy < 0.1):
        print("Low Rate Attack Detected because of entropy")
        LOW_RATE_FLAG = True
        return True

def get_entropy(data):
    from scipy.stats import entropy
    data = data.dropna()
    histogram, _ = np.histogram(data, bins=100)
    return entropy(histogram)


def check_flow_durations(data):
    global HIGH_RATE_FLAG, LOW_RATE_FLAG
    
    mean_removed = data['removed_flow_average_duration'].mean()
    average_flow_duration_on_table_last_row = data['average_flow_duration_on_table'].iloc[-1]
    ## if the average flow duration is bigger then idle timeout and mean removed is bigger than then the now average flow duration then it can be a low rate attack
    ## average_flow_duration_on_table_last_row > IDLE_TIMEOUT and 
    # TODO removeların avg duration'ının şu ankinden fazla olması nasıl low rate'i kanıtlıyor?
    if (average_flow_duration_on_table_last_row - mean_removed  > DURATION_THRESHOLD):
        print("Low Rate Attack Detected because of flow durations")
        LOW_RATE_FLAG = True
        return True

        
def detect_attack(data):
    ##TODO check the occupancy rate if it is higher than 0.8 then general attack can be occured
    # TODO aslında burada 5 batch var mı diye bakıyor, sonraki kontroller niye var o zaman, ama ilk high rate saldırıyla başlasa nolur
    if(len(data) < 5 ):
        print('There is no enough data')
        pass
    
    get_packet_in_rate(data)
    ##TODO Bu ikisini andlemek mantikli olabilir LOW_RATE
    get_occupancy_rate(data)
    check_flow_durations(data)
    
    



      
        
        
        
        
          
      
