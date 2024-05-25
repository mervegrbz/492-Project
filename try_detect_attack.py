from dataclasses import dataclass
import time
import statistics


@dataclass
class OccupancyRate:
    occupancy_rate: float
    time: float

# Simulated list of occupancy rates for demonstration
occupancy_rates = [
    OccupancyRate(0.45, time.time() - 20),
    OccupancyRate(0.48, time.time() - 15),
    OccupancyRate(0.51, time.time() - 10),
    OccupancyRate(0.43, time.time() - 5),
    OccupancyRate(0.45, time.time()),
    OccupancyRate(0.49, time.time() + 5),
    OccupancyRate(0.52, time.time() + 10),
    OccupancyRate(0.56, time.time() + 15),
    OccupancyRate(0.61, time.time() + 20)
]

def check_for_attack(occupancy_rates):
    if len(occupancy_rates) < 4:
        return False  # Not enough data to compare
    
    # Calculate the differences between consecutive occupancy rates
    differences = []
    # do that for previous 4 occupancy rates
    for i in range(len(occupancy_rates) - 5, len(occupancy_rates) - 1):
        rate_difference = occupancy_rates[i+1].occupancy_rate - occupancy_rates[i].occupancy_rate
        differences.append(rate_difference)
    print("differences: ")
    print(differences)
    # Check for consistent or increasing trend in differences
    last_diff = 0.0
    for diff in differences:
        # if occupancy rate increased and last occupancy rate and currents are close
        if (diff > 0.01 and (diff - last_diff < 0.015 or diff - last_diff > 0.015)):
            last_diff = diff  # No consistent increase
        else:
            return False
        
    # If we reached here, there is a consistent or increasing trend
    return True

# Example usage
attack_detected = check_for_attack(occupancy_rates)
print("Attack detected:", attack_detected)


@dataclass
class RemovedCount:
    removed_count: int
    time: float

# Example list of removed flow counts
removed_flow_counts = [
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(9, time.time() - 60),
    RemovedCount(10, time.time() - 100),
    RemovedCount(12, time.time() - 80),
    RemovedCount(9, time.time() - 60),
    RemovedCount(5, time.time() - 40),
    RemovedCount(6, time.time() - 20),
    RemovedCount(5, time.time()),
    RemovedCount(4, time.time() + 20),
    RemovedCount(2, time.time() + 40),
]

# compare the last 4 removed flow counts in the switch's mean and the last 20 counts of the switch
def check_removed_flows(removed_flow_counts):
    
    # Calculate the mean and standard deviation of all recorded removed flow counts
    all_counts = [rc.removed_count for rc in removed_flow_counts]
    mean_count = statistics.mean(all_counts)
    st_dev = statistics.stdev(all_counts)
    print(mean_count)
    print(st_dev)

    # Assume not enough data to perform robust statistical analysis
    analysis_index = 20
    last_indices = 5
    compare_for_lately = False
    if len(removed_flow_counts) > analysis_index:
        compare_for_last_20 = True  


    # Extract the last 4 removed flow counts
    last_counts = [rc.removed_count for rc in removed_flow_counts[-last_indices:]]
    print(last_counts)

    # Check if all of last four are significantly below the mean and within one standard deviation
    if all(x < mean_count - st_dev for x in last_counts):
        if (compare_for_last_20):
            lately_counts = all_counts[-analysis_index:-last_indices]
            print(lately_counts)
            lately_mean_count = statistics.mean(lately_counts)
            lately_st_dev = statistics.stdev(lately_counts)
            print(lately_mean_count)
            print(lately_st_dev)
            if (all(x < lately_mean_count - lately_st_dev for x in last_counts)):
                return True
            else:
                return False
        else:
            return True  # The last four counts are significantly lower than typical values
    
    return False

# Example usage
attack_detected = check_removed_flows(removed_flow_counts)
print("Potential issue detected:", attack_detected)


# directly deleted from switch_class because of duplicating
"""
	# checks whether flow count exceed capacity 
	# convert it to length of flow_table if it works fine
	def exceed_capacity(self):
		isExceed = ((len(self.flow_table) + 1 - self.flow_removed)/self.capacity) > CAPACITY_THRESHOLD
		if (isExceed):
			Detection(switch=self, detection_type= Detection_TYPE.GENERAL.value, switch_app=self.switch_app)
		return isExceed
	

	# flow_removed 0 mı yapmalıyız, ama o sırada gelen olursa kaydeder miyiz?
	# it stores the cumulative number of removed flows to compare them later
	def store_removed_flow_count(self):
		removed_count_before = 0
		if (len(self.removed_flow_counts) > 0):
			removed_count_before = self.removed_flow_counts[-1].removed_count
		
		current_remove_count = self.n_flow_removed - removed_count_before
		self.removed_flow_counts.append(flow_removed_count)


"""

# how I used in switch_class
"""
	# it compares the previous occupancy rates, and if it observes occupancy rates increased properly it returns true
	def check_previous_occupancy_rates(self):
		if len(self.occupancy_rates) < 4:
			return False  # Not enough data to compare
		
		# Calculate the differences between consecutive occupancy rates
		differences = []
		# do that for previous 4 occupancy rates
		for i in range(len(self.occupancy_rates) - 5, len(self.occupancy_rates) - 1):
			rate_difference = self.occupancy_rates[i+1].occupancy_rate - self.occupancy_rates[i].occupancy_rate
			differences.append(rate_difference)

		# Check for consistent or increasing trend in differences
		last_diff = 0.0
		for diff in differences:
			# if occupancy rate increased and last occupancy rate and currents are close
			if (diff > 0.01 and (diff - last_diff < 0.015 or diff - last_diff > 0.015)):
				last_diff = diff  # No consistent increase
			else:
				return False
			
		# If we reached here, there is a consistent or increasing trend
		return True


    # TODO batch için len flow_removed difflerinden benzer mantık implement edilebilir
    # compare the last 5 removed flow counts in the switch's mean and the last 20 counts of the switch
	# if the last ones are smaller than mean - st.dev it returns true
	def check_removed_flows(self):
		
		# Calculate the mean and standard deviation of all recorded removed flow counts
		all_counts = [rc.removed_count for rc in self.removed_flow_counts]
		mean_count = statistics.mean(all_counts)
		st_dev = statistics.stdev(all_counts)
		analysis_index = 20
		last_indices = 5

		# Assume not enough data to perform robust statistical analysis
		compare_for_lately = False
		if len(self.removed_flow_counts) > analysis_index:
			compare_for_lately = True  


		# Extract the last 4 removed flow counts
		last_counts = [rc.removed_count for rc in self.removed_flow_counts[-last_indices:]]
		print(last_counts)

		# Check if all of last four are significantly below the mean and within one standard deviation
		if all(x < mean_count - st_dev for x in last_counts):
			if (compare_for_lately):
				lately_counts = all_counts[-analysis_index:-last_indices]
				lately_mean_count = statistics.mean(lately_counts)
				lately_st_dev = statistics.stdev(lately_counts)
				if (all(x < lately_mean_count - lately_st_dev for x in last_counts)):
					return True
				else:
					return False
			else:
				return True  # The last four counts are significantly lower than typical values
		
		return False

    # TODO batchten belki bakılabilir ama batchte 5 saniye var? 
	# if current packet_in_count in a sec exceed the threshold call for every sec
	def is_high_rate_attack(self):
		
		# this scenerio is for not removing the packet in count, if we will remove for optimize our system this should be changed
		previous_packet_in_count = 0
		if (len(self.packet_in_counts_in_sec) > 0):
			previous_packet_in_count = self.packet_in_counts_in_sec[-1]

		current_packet_in_count = len(self.packet_in_counts_in_sec) - previous_packet_in_count
		
		
		# Calculate the mean and standard deviation of all recorded removed flow counts
		all_counts = [count for count in self.packet_in_counts_in_sec]
		mean_count = statistics.mean(all_counts)
		st_dev = statistics.stdev(all_counts)
		analysis_index = 10

		# Assume not enough data to perform robust statistical analysis
		compare_for_lately = False
		if len(self.packet_in_counts_in_sec) > analysis_index:
			compare_for_lately = True  
		
		self.packet_in_counts_in_sec.append(current_packet_in_count) # append current packet_in count

		# if it is more than 5 times of the average
		if (current_packet_in_count > 5*(mean_count + st_dev)):
			# compare for last 10 packet_in count (maybe something changed on the network)
			if (compare_for_lately):
				lately_counts = all_counts[-analysis_index:-1]
				lately_mean_count = statistics.mean(lately_counts)
				lately_st_dev = statistics.stdev(lately_counts)
				if (current_packet_in_count > 3*(lately_mean_count + lately_st_dev)):
					return True
				else:
					return False
			else: 
				return True
		return False

	# this method calculates occupancy rate, then compare the last 5 of them if it's suspect then compare the last 5 removed flow counts if it's also suspect then returns True
	def is_low_rate_attack(self):
		self.store_removed_flow_count(self)
		if (self.check_previous_occupancy_rates(self)):
			if (self.check_removed_flows(self)):
				return True
				
		return False

    	
	# get stats from controller's _flow_stats_reply_handler, detection type can be low_rate or high_rate
	# stats is a list that consists each flow as a dictionary
	def get_stats(self, stats):
		if (self.detections != []):
			calling_detection_module = self.detections[-1] # call the lately running detection module
			if (calling_detection_module.detection_type == Detection_TYPE.LOW_RATE.value):
				stats_in_increased_occupancy_rate = [stat for stat in stats if stat['duration'] < 5*4]
				calling_detection_module.start_low_rate_detection(stats_in_increased_occupancy_rate, stats)

	# it checks whether it's under attack, if so it will start detection module
	def check_for_attacks(self, check_for_both):
		if (self.is_high_rate_attack()):
			trigger_detection = Detection(switch=self, detection_type= Detection_TYPE.HIGH_RATE.value, switch_app=self.switch_app) 
			self.detections.append(trigger_detection)
		# when check for both high (every sec) and low rate attacks (every 5s)
		if (check_for_both):
			if (self.is_low_rate_attack()):
				trigger_detection = Detection(switch=self, detection_type= Detection_TYPE.LOW_RATE.value, switch_app=self.switch_app) 
				self.detections.append(trigger_detection)

"""