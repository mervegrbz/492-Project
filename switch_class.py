
import time
from enum import Enum
import numpy as np
import pandas as pd
import data_classes as data_model
from detection import *
import statistics
from detector import detect_attack
from parameters import TABLE_CAPACITY, UPPER_THRESHOLD_STD_DEV, MEAN_THRESHOLD, LOWER_THRESHOLD_STD_DEV, CAPACITY_THRESHOLD, HIGH_RATE_FLAG, LOW_RATE_FLAG, IDLE_TIMEOUT
from apscheduler.schedulers.background import BackgroundScheduler


# we may arrange it w.r.t official document https://ryu.readthedocs.io/en/latest/ofproto_v1_3_ref.html command enumaration
'''
OFPFC_ADD
OFPFC_MODIFY
OFPFC_MODIFY_STRICT
OFPFC_DELETE
OFPFC_DELETE_STRICT
'''
# enumaration of flow operations 
class FLOW_OPERATION(Enum):
	ADD = 1
	MODIFY = 2
	DELETE = 3

# this is a switch class, to monitor the switch's features without getting from stat request
class Switch:
	# lists
	datapath  = None # datapath of the switch
	packet_ins = [] # packet_in list, we can use it to store its mac address first,  when we get the flow_mod, updating the flow table w.r.t this and flow mod would be ben eficial.
	flow_table = [] # flows with features from merging packet_in's and add_flow events
	flow_removed = [] # flows that are removed from table, that will use in averages of flows existing
	occupancy_rates = [] # occupancy_rate for comparing switch's occupancy in time accordingly
	removed_flow_counts = [] # this is for comparing removed flow counts in time accordingly
	packet_in_counts_in_sec = [] # this is for comparing packet in count in a sec to compare whether there is a high-rate attack
	overload_timestamps = []
	detections = [] # for sending stat request's results to the corresponding detection module
	connection_time = 0
	n_errors = 0
	datapath_id = 0 # switch's id
	n_buffers = 0 
	n_tables = 0 # number of flow tables in the switch
	n_packet_in = 0 # cumulative packet in count
	n_flow_removed = 0 #TODO  is it required? isn't it same with len(flow_removed)
	flow_mods = 0 # number of added flows into the table (OFPFC_ADD)
	flow_id = 0 # this will help us to match packet_in and OFPFC_ADD messages, update the table correspondingly
	capabilities = 0 # flow capabilities of flow tables
	idle_timeout = IDLE_TIMEOUT
	schedular_iteration = 0

	def __init__(self, connection_time, datapath_id, n_buffers, n_tables, capabilities, datapath, switch_app):
		self.connection_time = connection_time
		self.datapath_id = datapath_id
		self.n_buffers = n_buffers
		self.n_tables = n_tables
		self.capabilities = capabilities
		self.capacity = TABLE_CAPACITY
		self.packet_in_rates = []
		columns = ['timestamp', 'capacity_used', 
             'removed_flow_average_duration', 'removed_flow_byte_per_packet',
             'average_flow_duration_on_table', 'packet_in_rate', 'number_of_errors',
             'flow_table_stats', 'removed_table_stats']
		self.history_batches = pd.DataFrame(columns=columns)  
		self.flow_rules = pd.DataFrame(columns=['ipv4_src','ipv4_dst','port_src','port_dst','ip_proto', 'actions', 'cookie', 'duration_sec', 'byte_count', 'packet_count', 'idle_timeout', 'timestamp'])
		self.scheduler = BackgroundScheduler()
		self.scheduler.add_job(self.flow_table_stats, 'interval', seconds=5)
		self.scheduler.start()

	# this function calculates the flow's occupancy rate, if it is more than threshold -> it will add its time into the overload_timestamps
	# returns the occupancy rate of the switch
	def calc_occupance_rate(self):
		# TODO reason should be add
		used_capacity = len(self.flow_table)
		if ((used_capacity / self.capacity) > CAPACITY_THRESHOLD):
			overload_time = time.time()
			self.overload_timestamps.append(overload_time)
			# print("Switch %s is overloaded" % self.datapath_id)
		print(len(self.flow_table))
		# TODO data classtan çıkar
		current_occupancy_rate = data_model.OccupancyRate(used_capacity / self.capacity,time.time())
		self.occupancy_rates.append(current_occupancy_rate)
		return used_capacity / self.capacity

	# this function calculates the statistics from removed flows. 
	# it calculates and returns flow_average_duration, flow_average_byte_per_packet
	def calc_removed_flows(self):
		average_duration = 0
		average_byte_per_packet = 0	
		# TODO get the last N elements of the removed flows to monitor change
		for flow in self.flow_removed:
			duration_sec = flow['duration_sec']
			reason = flow['reason']
			byte_count = flow['byte_count']
			packet_count = flow['packet_count']

			average_byte_per_packet += byte_count/packet_count  if packet_count > 0 else 0
			average_duration += duration_sec

		flow_average_duration = average_duration/len(self.flow_removed) if (len(self.flow_removed)>0) else 0
		flow_average_byte_per_packet = average_byte_per_packet / len(self.flow_removed) if (len(self.flow_removed)>0) else 0
		return flow_average_duration, flow_average_byte_per_packet

	# this function updates the flow table, if the operation is ADD, append the flow into the flowtable,
	# else if it's delete, delete it from the table by using its match criteria
	def update_flow_table(self, current_flow, operation):
		if operation == FLOW_OPERATION.ADD:
				if(len(self.flow_table)>=self.capacity):
					return
				self.flow_table.append(current_flow, operation)
				self.append_flow_rules(current_flow)
				self.flow_mods += 1
		elif operation == FLOW_OPERATION.DELETE:
				for flow in self.flow_table:
						#TODO cookieden emin miyiz neden match'e bakmadık?
						if flow['cookie'] == current_flow['cookie']:
								self.append_flow_rules(flow, operation)
								self.flow_table.remove(flow)
								self.flow_removed.append(current_flow)
								self.n_flow_removed += 1


	def append_flow_rules(self, flow, operation):
		_flow = {}
		## switch supports only three protocols for now	
		if(operation == FLOW_OPERATION.DELETE):
			## find the flow rule in the flow_rules and insert the duration_sec, byte_count, packet_count
			for index, row in self.flow_rules.iterrows():
				if(flow['cookie']== row['cookie']):
					self.flow_rules.at[index, 'duration_sec'] = flow['duration_sec']
					self.flow_rules.at[index, 'byte_count'] = flow['byte_count']
					self.flow_rules.at[index, 'packet_count'] = flow['packet_count']
					break
		if (operation == FLOW_OPERATION.ADD):
			if (flow['ip_proto'] == 6):
				_flow = {'ipv4_src': flow['ipv4_src'], 'ipv4_dst': flow['ipv4_dst'], 'port_src': flow['tcp_src'], 'port_dst': flow['tcp_dst'], 'ip_proto': flow['ip_proto'], 'actions': flow['actions'], 'cookie': flow['cookie'], 'idle_timeout': flow['idle_timeout'], 'timestamp': time.time()}
			if (flow['ip_proto'] == 17):
				_flow = {'ipv4_src': flow['ipv4_src'], 'ipv4_dst': flow['ipv4_dst'], 'port_src': flow['udp_src'], 'port_dst': flow['udp_dst'], 'ip_proto': flow['ip_proto'], 'actions': flow['actions'], 'cookie': flow['cookie'], 'idle_timeout': flow['idle_timeout'], 'timestamp': time.time()}
			if (flow['ip_proto'] == 1):
				_flow = {'ipv4_src': flow['ipv4_src'], 'ipv4_dst': flow['ipv4_dst'], 'port_src': flow['icmpv4_type'], 'port_dst': flow['icmpv4_code'], 'ip_proto': flow['ip_proto'], 'actions': flow['actions'], 'cookie': flow['cookie'], 'idle_timeout': flow['idle_timeout'], 'timestamp': time.time()}
			self.flow_rules.loc[len(self.flow_rules)] = _flow
		
	# this function calculates average duration of flows in the flow table
	def inspect_flow_table(self):
		total_duration = 0
		for flow in self.flow_table:
			now = time.time()
			total_duration += now - int(flow['timestamp'])
		average_duration = total_duration/len(self.flow_table) if len(self.flow_table) > 0 else 0
		return average_duration

	def count_unique(self, values):
		count_dict = {}
		for value in values:
				if value in count_dict:
						count_dict[value] += 1
				else:
						count_dict[value] = 1
		return count_dict

	def flow_mod_statistics(self, table): 
		stats = []

		ip_proto  = [i['match']['ip_proto'] for i in table if 'ip_proto' in i['match']]
		ip_src = [i['match']['ipv4_src'] for i in table if 'ipv4_src' in i['match']]
		ip_dst = [i['match']['ipv4_dst'] for i in table if 'ipv4_dst' in i['match']]
		
		count_dict = self.count_unique(ip_proto)
		stats.append(count_dict)
		## TODO add the average duration for each ip_src and ip_dst
		count_dict = self.count_unique(ip_src)
		stats.append(count_dict)
		count_dict = self.count_unique(ip_dst)
		stats.append(count_dict)
		return stats
		
	# This method may work every seconds to keep track of the flow table, it has a counter and when it reaches 5 (every 5 sec) it checks for low-rate attacks
	def flow_table_stats(self):
		print("flow_table_stats")
		self.schedular_iteration += 1
		if (self.schedular_iteration == 1):
			self.schedular_iteration = 0
			# self.check_for_attacks(True)
			capacity_used = self.calc_occupance_rate()
			flow_average_duration, flow_average_byte_per_packet = self.calc_removed_flows()
			average_flow_duration_on_table = self.inspect_flow_table()
			flow_table_stats = self.flow_mod_statistics(self.flow_table)
			removed_table_stats = self.flow_mod_statistics(self.flow_removed)
			print(time.time(), capacity_used, flow_average_duration, flow_average_byte_per_packet, average_flow_duration_on_table)
			self.history_batches.loc[len(self.history_batches)] = {'timestamp': time.time(), 'capacity_used': capacity_used, 'removed_flow_average_duration': flow_average_duration,
																		'removed_flow_byte_per_packet': flow_average_byte_per_packet, 'average_flow_duration_on_table': average_flow_duration_on_table,
																		'packet_in_rate': self.n_packet_in, 'number_of_errors': self.n_errors ,'flow_table_stats': flow_table_stats, 'removed_table_stats': removed_table_stats }
			##TODO call the flow_mod_statistics method
			detect_attack(self.history_batches)
			

			if(len(self.history_batches) > 30 ) :
				self.history_batches.to_csv(f'history_batches_{self.datapath_id}.csv')

		
	def get_related_batch(self, num_of_batch=5):
		return self.history_batches[-num_of_batch:] if len(self.history_batches)>num_of_batch else self.history_batches
   
	# checks whether flow count exceed capacity 
	# TODO convert it to length of flow_table if it works fine
	def exceed_capacity(self):
		isExceed = ((self.flow_mods + 1 - self.flow_removed)/self.capacity) > CAPACITY_THRESHOLD
		if (isExceed):
			trigger_detection = Detection(switch=self, detection_type= Detection_TYPE.GENERAL.value, switch_app=self.switch_app)
			self.detections.append(trigger_detection)
		return isExceed
	

	# TODO flow_removed 0 mı yapmalıyız, ama o sırada gelen olursa kaydeder miyiz?
	# it stores the cumulative number of removed flows to compare them later
	def store_removed_flow_count(self):
		removed_count_before = 0
		if (len(self.removed_flow_counts) > 0):
			removed_count_before = self.removed_flow_counts[-1].removed_count
		
		current_remove_count = self.n_flow_removed - removed_count_before
		flow_removed_count = data_model.RemovedCount(removed_count=current_remove_count, time=time.time())
		self.removed_flow_counts.append(flow_removed_count)


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
	
	# TODO call for every sec
	# if current packet_in_count in a sec exceed the threshold
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
		if len(self.removed_flow_counts) > analysis_index:
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

	# TODO call for every 5 sec
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

