from enum import Enum
from typing import List
import numpy as np
from datetime import datetime
import statistics

# enumaration type of detection
class Detection_TYPE(Enum):
	LOW_RATE = 1
	HIGH_RATE = 2
	GENERAL = 3

class Detection:

  switch = None
  detection_type = 1

  # initialize detection with switch and the detection type
  def __init__(self, switch, detection_type, switch_app):
    from switch_class import Switch  # Import here to avoid circular dependency at module load
    assert isinstance(switch, Switch)
    from switch import SimpleSwitch13  # Import here to avoid circular dependency at module load
    assert isinstance(switch_app, SimpleSwitch13)
    print("init-detection with type: " + str(detection_type))
    self.switch = switch
    self.detection_type = detection_type
    self.switch_app = switch_app
    self.check_for_detection()

  def check_for_detection(self):
    if (self.detection_type == Detection_TYPE.LOW_RATE.value):
      self.low_rate_detection()
    elif (self.detection_type == Detection_TYPE.HIGH_RATE.value):
      self.high_rate_detection()
    else:
      self.general_detection()
  

  def low_rate_detection(self):
     print("low_rate_detection")
     removed_flows_enter_times = [rf.timestamp-rf.duration_nsec for rf in self.switch.flow_removed] # TODO check 
     removed_flows_removed_times = [rf.timestamp for rf in self.switch.flow_removed]
     occupancy_rates = [o_r.occupancy_rate for o_r in self.switch.occupancy_rates]
     if (self.is_low_rate(removed_enter_times=removed_flows_enter_times,  removed_removing_times=removed_flows_removed_times, packet_in_counts=self.switch.packet_in_counts_in_sec, occupancy_rates=occupancy_rates)):
        self.switch_app.send_flow_stats_request(self.switch.datapath)
     
  # ml algorithm for detecting whether it is a low rate attack
  def is_low_rate(self, removed_enter_times, removed_removing_times, packet_in_counts, occupancy_rates):
     return True
  
  # started low rate detection with stats in increased occupancy rate time and general stats
  def start_low_rate_detection(self, stats_increased, stats):
     print("start_low_rate_detection")
     #calc avg byte per sec for flows that appends in increased occupance rate times
     print("stats_increased")
     avg_byte_sec_increased = self.calc_avg_bytes_per_sec(stats_increased)
     if (avg_byte_sec_increased < 3):
        print("stats")
        mean_byte_per_sec, mean_packet_per_secs, mean_byte_per_packets = self.calc_avges(stats)
        # TODO add logic here

  
  #calc avg byte per sec for flows that appends in increased occupance rate times
  def calc_avg_bytes_per_sec(self, stats):
     byte_per_secs = [stat['byte_count_per_second'] for stat in stats]
     if (byte_per_secs != []):
        mean = statistics.mean(byte_per_secs)
        print("avg byte per sec: ")
        print(mean)
        return mean
     print("bombos")
     return 0
  
  #calc avg byte per sec, packet per sec, byte per pack
  def calc_avges(self, stats):
    byte_per_secs = [stat['byte_count_per_second'] for stat in stats]
    packet_per_secs = [stat['packet_count_per_second'] for stat in stats]
    byte_per_packets = [stat['byte_per_packet'] for stat in stats]
    mean_byte_per_sec = 0
    mean_packet_per_secs = 0
    mean_byte_per_packets = 0
    if (byte_per_secs != []):
      mean_byte_per_sec = statistics.mean(byte_per_secs)
      print("avg byte per sec: ")
      print(mean_byte_per_sec)
    if (packet_per_secs != []):
        mean_packet_per_secs = statistics.mean(packet_per_secs)
        print("avg packet per sec: ")
        print(mean_packet_per_secs)
    if (byte_per_packets != []):
        mean_byte_per_packets = statistics.mean(packet_per_secs)
        print("avg packet per sec: ")
        print(mean_byte_per_packets)

    return mean_byte_per_sec,mean_packet_per_secs,mean_byte_per_packets


  def high_rate_detection(self):
    flow_table = self.switch.flow_table
    timestamp = datetime.now()
    timestamp = timestamp.timestamp()
    flows_duration_smaller_than_idle_timeout = [flow for flow in flow_table if (flow.timestamp - timestamp)< flow.idle_timeout]
    
    if (len(flows_duration_smaller_than_idle_timeout) * 4 > len(flow_table)): # if newly appended flows are at least %25 of the flow table 
      print("You are under high-rate attack")  
      for flow in flow_table:
        print("Delete flow with match: " + str(flow.match))  
        self.switch_app.delete_flows(self.switch.datapath, flow.match, flow.priority)
    
	
  def general_detection(self):
    packet_in_counts = self.switch.packet_in_counts_in_sec
    if (len(packet_in_counts) > 2):
      packet_ins_last_two_sec = packet_in_counts[-1] + packet_in_counts[-2]
      mean = np.mean(packet_in_counts)
      stdev = np.std(packet_in_counts)
      if (packet_ins_last_two_sec > 5*(mean+stdev)):
        self.high_rate_detection()
      else:
         self.low_rate_detection()
      
    
    
