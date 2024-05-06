from enum import Enum
from typing import List

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
    print("init-detection")
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
        self.start_low_rate_detection()
     
  # ml algorithm for detecting whether it is a low rate attack
  def is_low_rate(self, removed_enter_times, removed_removing_times, packet_in_counts, occupancy_rates):
     return True
  
  def start_low_rate_detection(self):
     print("start_low_rate_detection")
     self.switch_app.send_flow_stats_request(self.switch.datapath)
     # TODO how much we need to wait for stats?
     # what about saving detections in a list, and trigger its method? Seems ok I think

  def high_rate_detection(self):
     pass
	
  def general_detection(self):
     pass
    
    
