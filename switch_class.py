
import time
from enum import Enum
import numpy as np
import pandas as pd
from dataclasses import dataclass

UPPER_THRESHOLD_STD_DEV = 0.1
MEAN_THRESHOLD = 0.1
LOWER_THRESHOLD_STD_DEV = 0.01
CAPACITY_THRESHOLD = 0.8

@dataclass
class OccupancyRate:
    occupancy_rate: float
    time: float

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
	packet_ins = [] # packet_in list, we can use it to store its mac address first,
	# when we get the flow_mod, updating the flow table w.r.t this and flow mod would be beneficial.
	flow_table = [] # flows with features from merging packet_in's and add_flow events
	flow_removed = [] # flows that are removed from table, that will use in averages of flows existing
	connection_time = 0
	datapath_id = 0 # switch's id
	n_buffers = 0 
	n_tables = 0 
	n_packet_in = 0
	n_flow_removed = 0 #TODO  is it required? isn't it same with len(flow_removed)
	flow_mods = 0 # number of added flows into the table (OFPFC_ADD)
	capacity = 0
	capabilities = 0
	idle_timeout = 10
	flow_average_duration = 0
	flow_average_byte_per_packet = 0
	state = "Normal"
	overload_timestamps = []
	occupancy_rates = [] # occupancy_rate for comparing switch's occupancy in time accordingly
	history_batches = pd.DataFrame()

	def __init__(self, connection_time, datapath_id, n_buffers, n_tables, capabilities):
		self.connection_time = connection_time
		self.datapath_id = datapath_id
		self.n_buffers = n_buffers
		self.n_tables = n_tables
		self.capabilities = capabilities
		self.packet_in_rates = []
		columns = ['timestamp', 'capacity_used', 'removed_flow_average_duration', 'removed_flow_byte_per_packet', 'average_flow_duration_on_table', 'packet_in_mean', 'packet_in_std_dev', 'packet_in_diff_arr']
		self.history_batches = pd.DataFrame(columns=columns)

	# this function calculates the flow's occupancy rate, if it is more than threshold -> it will add its time into the overload_timestamps
	# returns the occupancy rate of the switch
	def calc_flow_stats(self):
		# TODO reason should be add
		used_capacity = self.flow_mods - self.n_flow_removed # flow count of the switch
		if ((used_capacity / self.capacity) > CAPACITY_THRESHOLD):
			overload_time = time.time()
			self.overload_timestamps.append(overload_time)
			print("Switch %s is overloaded" % self.datapath_id)
		#TODO is it ok?
		#current_occupancy_rate = OccupancyRate(used_capacity / self.capacity,time.time())
		#self.occupancy_rates.append(current_occupancy_rate)
		return used_capacity / self.capacity

	# this function calculates the statistics from removed flows. 
	# it calculates and returns flow_average_duration, flow_average_byte_per_packet
	def calc_removed_flows(self):
		average_duration = 0
		average_byte_per_packet = 0
		# TODO get the last N elements of the removed flows to monitor change
		for i in self.flow_removed:
			duration_sec = i.duration_sec
			reason = i.reason
			byte_count = i.byte_count
			packet_count = i.packet_count
			average_byte_per_packet += byte_count/packet_count
			average_duration += duration_sec
		self.flow_average_duration = average_duration/len(self.flow_removed)
		self.flow_average_byte_per_packet = average_byte_per_packet / len(self.flow_removed)
		return self.flow_average_duration, self.flow_average_byte_per_packet

	# this function updates the flow table, if the operation is ADD, append the flow into the flowtable,
	# else if it's delete, delete it from the table by using its match criteria
	def update_flow_table(self, flow, operation):
		if operation == FLOW_OPERATION.ADD:
				self.flow_table.append(flow)
				self.flow_mods += 1
		if operation == FLOW_OPERATION.DELETE:
				for i in self.flow_table:
						if i.match == flow.match:
								self.flow_table.remove(i)
								self.flow_removed.append(i)
								self.n_flow_removed += 1

	# this function calculates average duration of flows in the flow table
	def inspect_flow_table(self):
		total_duration = 0
		##
		for i in self.flow_table:
			now = time.time()
			total_duration += now - i.timestamp
		average_duration = total_duration/len(self.flow_table)
		print("Average duration of flows in flow table is %s" % average_duration)
		return average_duration

	# This method calculates statistics of occupancy rates
	# TODO: This method should be called by the scheduler
	def occupancy_scheduler(self):
		diff_arr = np.diff(self.occupancy_rates)
		std_dev = np.std(diff_arr)
		mean = np.mean(diff_arr)

		occupancy_rate = len(self.flow_table)/self.capacity
		self.occupancy_rates.append(occupancy_rate)

		new_diff_arr = np.diff(self.occupancy_rates)
		new_std_dev = np.std(new_diff_arr)
		new_mean = np.mean(new_diff_arr)

		if abs(new_mean - mean) > MEAN_THRESHOLD:
			print("Mean threshold exceeded")
			print('Switch table load fast')

	# TODO packet_ins should be used to use that, when we calculate rate, we need to remove all elements from the list.
	# TODO we shouldn't remove packet_in if its flow_add isn't called yet to updating flow table correspondingly
	def packet_in_rates_calc(self):
		diff_arr = np.diff(self.packet_in_rates)
		std_dev = np.std(diff_arr)
		mean = np.mean(diff_arr)

		self.packet_in_rates.append(len(self.packet_ins))

		new_diff_arr = np.diff(self.packet_in_rates)
		new_std_dev = np.std(new_diff_arr)
		new_mean = np.mean(new_diff_arr)

		if abs(new_mean - mean) > MEAN_THRESHOLD:
			print("Mean threshold exceeded")
			print('Packet_in too much')
		return new_mean, new_std_dev, new_diff_arr
	
	# This method may work every 5 seconds to keep track of the flow table
	def flow_table_stats(self):
		capacity_used = self.calc_flow_stats()
		flow_average_duration, flow_average_byte_per_packet = self.calc_removed_flows()
		average_flow_duration_on_table = self.inspect_flow_table()
		mean, std_dev, diff_arr = self.packet_in_rates_calc()
		self.history_batches.add([time.time(), capacity_used, flow_average_duration,
															flow_average_byte_per_packet, average_flow_duration_on_table, mean, std_dev, diff_arr])
