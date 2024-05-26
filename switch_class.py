
import time
from enum import Enum
import numpy as np
import pandas as pd
import data_classes as data_model
from detection import *
import statistics
from predictor import *
from parameters import *
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
	flow_table = [] # flows with features from merging packet_in's and add_flow events
	flow_removed = [] # flows that are removed from table, that will use in averages of flows existing
	overload_timestamps = []
	connection_time = 0 #timestamp when switch is created
	n_errors = 0
	datapath_id = 0 # switch's id
	n_buffers = 0 
	n_tables = 0 # number of flow tables in the switch
	n_packet_in = 0 # cumulative packet in count
	capabilities = 0 # flow capabilities of flow tables
	idle_timeout = IDLE_TIMEOUT

	def __init__(self, connection_time, datapath_id, n_buffers, n_tables, capabilities, datapath, switch_app):
		self.connection_time = connection_time
		self.datapath_id = datapath_id
		self.n_buffers = n_buffers
		self.n_tables = n_tables
		self.capabilities = capabilities
		self.capacity = TABLE_CAPACITY
		columns = ['timestamp', 'capacity_used', 
             'removed_flow_average_duration', 'removed_flow_byte_per_packet', 'removed_average_byte_per_sec',
             'average_flow_duration_on_table', 'packet_in_rate', 'removed_flows_count', 'number_of_errors',
             'flow_table_stats', 'flow_table_stats_durations' 'removed_table_stats', 'removed_table_stats_durations', 'is_attack']
		self.history_batches = pd.DataFrame(columns=columns)  
		self.flow_rules = pd.DataFrame(columns=['ipv4_src','ipv4_dst','port_src','port_dst','ip_proto', 'actions', 'cookie', 'duration_sec', 'byte_count', 'packet_count', 'idle_timeout', 'timestamp'])
		self.scheduler = BackgroundScheduler()
		self.scheduler.add_job(self.flow_table_stats, 'interval', seconds=5)
		self.scheduler.start()

	# this function calculates the flow's occupancy rate, if it is more than threshold -> it will add its time into the overload_timestamps
	# returns the occupancy rate of the switch
	def calc_occupance_rate(self):
		used_capacity = len(self.flow_table)
		if ((used_capacity / self.capacity) > CAPACITY_THRESHOLD):
			overload_time = time.time()
			self.overload_timestamps.append(overload_time)
			# print("Switch %s is overloaded" % self.datapath_id)
		print(len(self.flow_table))
		return used_capacity / self.capacity

	# this function calculates the statistics from removed flows. 
	# it calculates and returns flow_average_duration, flow_average_byte_per_packet, average_byte_per_sec
	def calc_removed_flows(self):
		average_duration = 0
		average_byte_per_packet = 0	
		average_byte_per_sec = 0
		# TODO get the last N elements of the removed flows to monitor change
		for flow in self.flow_removed:
			duration_sec = flow['duration_sec']
			reason = flow['reason']
			byte_count = flow['byte_count']
			packet_count = flow['packet_count']
			
			average_byte_per_packet += byte_count/packet_count  if packet_count > 0 else 0
			average_duration += duration_sec
			average_byte_per_sec += byte_count/duration_sec  if duration_sec > 0 else 0

		flow_average_duration = average_duration/len(self.flow_removed) if (len(self.flow_removed)>0) else 0
		flow_average_byte_per_packet = average_byte_per_packet / len(self.flow_removed) if (len(self.flow_removed)>0) else 0
		average_byte_per_sec = average_byte_per_sec / len(self.flow_removed) if (len(self.flow_removed)>0) else 0
		return flow_average_duration, flow_average_byte_per_packet, average_byte_per_sec

	# this function updates the flow table, if the operation is ADD, append the flow into the flowtable,
	# else if it's delete, delete it from the table by using its match criteria
	def update_flow_table(self, current_flow, operation):
		if operation == FLOW_OPERATION.ADD:
			if(len(self.flow_table)>=self.capacity):
				return
			self.flow_table.append(current_flow)
			self.append_flow_rules(current_flow, operation)

		elif operation == FLOW_OPERATION.DELETE:
			for flow in self.flow_table:
				if flow['cookie'] == current_flow['cookie']:
					self.append_flow_rules(current_flow, operation)
					self.flow_table.remove(flow)
					# if flow removed not because of mitigation, append it to flow_removed list to use it later as a normal removed flows
					if (flow['reason'] == 'IDLE TIMEOUT' or flow['reason'] == 'HARD TIMEOUT'):
						is_attack = flow['is_attack']
						current_flow['is_attack'] = is_attack  # Carry forward the is_attack field
						self.flow_removed.append(current_flow)


	def append_flow_rules(self, flow, operation):
		_flow = {}
		## switch supports only three protocols for now	
		if(operation == FLOW_OPERATION.DELETE):
			row_index = self.flow_rules.loc[self.flow_rules['cookie'] == flow['cookie']].index[0]

			## find the flow rule in the flow_rules and insert the duration_sec, byte_count, packet_count
			self.flow_rules.loc[row_index, 'duration_sec'] = flow['duration_sec']
			self.flow_rules.loc[row_index, 'byte_count'] = flow['byte_count']
			self.flow_rules.loc[row_index, 'packet_count'] = flow['packet_count']
		if (operation == FLOW_OPERATION.ADD):
			if (flow['match']['ip_proto'] == 6):
				_flow = {'ipv4_src': flow['match']['ipv4_src'], 'ipv4_dst': flow['match']['ipv4_dst'], 'port_src': flow['match']['tcp_src'], 'port_dst': flow['match']['tcp_dst'], 'ip_proto': flow['match']['ip_proto'], 'cookie': flow['cookie'], 'idle_timeout': flow['idle_timeout'], 'timestamp': time.time(), 'duration_sec': 0, 'byte_count': 0, 'packet_count': 0}
			if (flow['match']['ip_proto'] == 17):
				_flow = {'ipv4_src': flow['match']['ipv4_src'], 'ipv4_dst': flow['match']['ipv4_dst'], 'port_src': flow['match']['udp_src'], 'port_dst': flow['match']['udp_dst'], 'ip_proto': flow['match']['ip_proto'], 'cookie': flow['cookie'], 'idle_timeout': flow['idle_timeout'], 'timestamp': time.time(),'duration_sec': 0, 'byte_count': 0, 'packet_count': 0}
			if (flow['match']['ip_proto'] == 1):
				_flow = {'ipv4_src': flow['match']['ipv4_src'], 'ipv4_dst': flow['match']['ipv4_dst'], 'port_src': flow['match']['icmpv4_type'], 'port_dst': flow['match']['icmpv4_code'], 'ip_proto': flow['match']['ip_proto'], 'cookie': flow['cookie'], 'idle_timeout': flow['idle_timeout'], 'timestamp': time.time(),'duration_sec': 0, 'byte_count': 0, 'packet_count': 0}
			if (_flow !={}):
				self.flow_rules.loc[len(self.flow_rules)] = _flow
		
	# this function calculates average duration of flows in the flow table
	def average_duration_on_flow_table(self):
		total_duration = 0
		for flow in self.flow_table:
			now = time.time()
			total_duration += now - int(flow['timestamp'])
		average_duration = total_duration/len(self.flow_table) if len(self.flow_table) > 0 else 0
		return average_duration

	def count_unique(self, values):
		count_dict = {}
		avg_time_dict = {}
		for value in values:
			match = value[0]
			duration = value[1]
			if match in count_dict:
				count_dict[match] += 1
				avg_time_dict[match] = (avg_time_dict[match] + duration) / float(count_dict[match])
			else:
				count_dict[match] = 1
				avg_time_dict[match] = duration
		return count_dict, avg_time_dict

	def flow_mod_statistics(self, table, isRemoved): 
		stats = []
		avg_times = []
		ip_proto = []
		ip_src = []
		ip_dst = []
		
		# if is removed, we need to check duration_sec
		if (isRemoved):
			ip_proto  = [(i['match']['ip_proto'],i['duration_sec']) for i in table if 'ip_proto' in i['match']]
			ip_src = [(i['match']['ipv4_src'],i['duration_sec']) for i in table if 'ipv4_src' in i['match']]
			ip_dst = [(i['match']['ipv4_dst'],i['duration_sec']) for i in table if 'ipv4_dst' in i['match']]
		# else we need to compare timestamps
		else:
			now = time.time()
			ip_proto  = [(i['match']['ip_proto'],i['timestamp']-now) for i in table if 'ip_proto' in i['match']]
			ip_src = [(i['match']['ipv4_src'],i['timestamp']-now) for i in table if 'ipv4_src' in i['match']]
			ip_dst = [(i['match']['ipv4_dst'],i['timestamp']-now) for i in table if 'ipv4_dst' in i['match']]
		
		count_dict, avg_time_dict = self.count_unique(ip_proto)
		stats.append(count_dict)
		avg_times.append(avg_time_dict)
		count_dict, avg_time_dict = self.count_unique(ip_src)
		stats.append(count_dict)
		avg_times.append(avg_time_dict)
		count_dict, avg_time_dict = self.count_unique(ip_dst)
		stats.append(count_dict)
		avg_times.append(avg_time_dict)
		return stats, avg_times
		
	# This method may work every seconds to keep track of the flow table, it has a counter and when it reaches 5 (every 5 sec) it checks for low-rate attacks
	def flow_table_stats(self):

		capacity_used = self.calc_occupance_rate()
		flow_average_duration, flow_average_byte_per_packet, removed_average_byte_per_sec = self.calc_removed_flows()
		average_flow_duration_on_table = self.average_duration_on_flow_table()
		flow_table_stats, flow_table_stats_durations = self.flow_mod_statistics(self.flow_table, False)
		removed_table_stats, removed_table_stats_durations = self.flow_mod_statistics(self.flow_removed, True)
		is_attack = self.check_is_attack()
		print(time.time(), capacity_used, flow_average_duration, flow_average_byte_per_packet, average_flow_duration_on_table)
		self.history_batches.loc[len(self.history_batches)] = {'timestamp': time.time(), 'capacity_used': capacity_used, 'removed_flow_average_duration': flow_average_duration,
																	'removed_flow_byte_per_packet': flow_average_byte_per_packet, 'removed_average_byte_per_sec': removed_average_byte_per_sec, 'average_flow_duration_on_table': average_flow_duration_on_table,
																	'packet_in_rate': self.n_packet_in, 'removed_flows_count': len(self.flow_removed), 'number_of_errors': self.n_errors ,'flow_table_stats': flow_table_stats,
																	'flow_table_stats_durations': flow_table_stats_durations, 'removed_table_stats': removed_table_stats, 
																	'removed_table_stats_durations':removed_table_stats_durations, 'is_attack': is_attack}
		check_attack(self.history_batches)
		

		if(len(self.history_batches) > 30 ) :
			self.history_batches.to_csv(f'history_batches_{self.datapath_id}.csv')

		
	def get_related_batch(self, num_of_batch=5):
		return self.history_batches[-num_of_batch:] if len(self.history_batches)>num_of_batch else self.history_batches
	
	# check whether switch is under attack
	# TODO atak flowu varsa direkt atak da diyebiliriz, çoğunluk olunca da hangisi daha mantıklı? normal capacity %70'se çoğunluk olamaz mesela
	# ama ML eğitirken pek bir şey etkilemediği halde atak dersek de sorun olabilir.
	def check_is_attack(self):
		attack_flows = [flow for flow in self.flow_table if flow['is_attack']]
		normal_flows = [flow for flow in self.flow_table if not flow['is_attack']]
		if len(normal_flows) / 4.0 > len(attack_flows):
			return 0
		else:
			return 1
