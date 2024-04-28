
import time
from enum import Enum
import numpy as np
import pandas as pd

UPPER_THRESHOLD_STD_DEV = 0.1
MEAN_THRESHOLD = 0.1
LOWER_THRESHOLD_STD_DEV = 0.01


class FLOW_OPERATION(Enum):
	ADD = 1
	MODIFY = 2
	DELETE = 3


class Switch:
	packet_ins = []
	flow_table = []
	flow_removed = []
	connection_time = 0
	datapath_id = 0
	n_buffers = 0
	n_tables = 0
	n_packet_in = 0
	n_flow_removed = 0
	flow_mods = 0
	capacity = 0
	capabilities = 0
	idle_timeout = 10
	flow_average_duration = 0
	flow_average_byte_per_packet = 0
	state = "Normal"
	overload_timestamps = []
	occupancy_rates = []
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

	def calc_flow_stats(self):
		# todo reason should be add
		used_capacity = self.flow_mods - self.n_flow_removed
		if ((used_capacity / self.capacity) > 0.8):
			overload_time = time.time()
			self.overload_timestamps.append(overload_time)
			print("Switch %s is overloaded" % self.datapath_id)
		return used_capacity / self.capacity

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

	def inspect_flow_table(self):
		total_duration = 0
		##
		for i in self.flow_table:
			now = time.time()
			total_duration += now - i.timestamp
		average_duration = total_duration/len(self.flow_table)
		print("Average duration of flows in flow table is %s" % average_duration)
		return average_duration

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
