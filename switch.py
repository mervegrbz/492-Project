# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, HANDSHAKE_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv4, tcp, udp, icmp, in_proto
from ryu.lib.packet import ether_types
from ryu import utils
import data_classes as datamodel
from datetime import datetime

import switch_class

import schedule
import csv
flow_list = []

batch_number = 0

# writing logs into the file w.r.t batch number after that it will convert it to csv in analyzer class
def write_logs(batch_number, logs):
		filename = f"log_batch_{batch_number}.txt"
		with open(filename, mode='w') as file:
				for log in logs:

						file.write(str(log) + '\n')

# a simple switch class from OpenFlow 1.3 documentation (https://github.com/faucetsdn/ryu/blob/master/ryu/app/simple_switch_13.py)
class SimpleSwitch13(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	def __init__(self, *args, **kwargs):
			super(SimpleSwitch13, self).__init__(*args, **kwargs)
			self.banned_list = []
			self.white_list = []
			self.mac_to_port = {}
			self.switch_list = {} #consists of SwitchFeatures in dataclasses

	# when switch features comes to the controller, it will append its some features into the flow_list which we will use in our csv files
	# you can check for this link for following handler classes https://ryu.readthedocs.io/en/latest/ofproto_v1_3_ref.html
	@set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
	def switch_features_handler(self, ev):
			global flow_list
			datapath = ev.msg.datapath
			timestamp = ev.timestamp
			ofproto = datapath.ofproto
			parser = datapath.ofproto_parser
			datapath_id = datapath.id
			n_buffers = ev.msg.n_buffers
			n_tables = ev.msg.n_tables
			capabilities = ev.msg.capabilities

			switch = switch_class.Switch(timestamp, datapath_id, n_buffers, n_tables, capabilities, datapath, self)
			# adding switch to the switch list with its datapath_id
			self.switch_list[datapath_id] = switch

			flow_list.append({'type': 'SwitchFeatures', 'timestamp': timestamp, 'datapath_id': datapath_id,
												'n_buffers': n_buffers, 'n_tables': n_tables, 'capabilities': capabilities})

			match = parser.OFPMatch()
			actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
			# switch saves itselves without idle, hard timeout therefore not used send_flow
			self.add_flow(datapath, timestamp, 0, match, actions)

	# It will called when packet_in message comes to the controller
	def send_flow_mod(self, datapath, timestamp, match, actions, priority, buffer_id=None):
			ofp = datapath.ofproto
			ofp_parser = datapath.ofproto_parser
			idle_timeout = 10
			inst = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
			mod = None
			#in_port = match['in_port'] doesn't work because of L4 we need to consider
			if (buffer_id):
				mod = ofp_parser.OFPFlowMod(datapath, cookie=0, cookie_mask=0, table_id=0, command=ofp.OFPFC_ADD,
																		idle_timeout=idle_timeout, hard_timeout=0,priority=priority, buffer_id=buffer_id,
																		out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY, flags=ofp.OFPFF_SEND_FLOW_REM,
																		match=match, instructions=inst)
			else:
				mod = ofp_parser.OFPFlowMod(datapath, cookie=0, cookie_mask=0, table_id=0, command=ofp.OFPFC_ADD, idle_timeout=idle_timeout, hard_timeout=0,
																		priority=priority, out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
																		flags=ofp.OFPFF_SEND_FLOW_REM, match=match, instructions=inst)
			match_obj = {i['OXMTlv']['field']: i['OXMTlv']['value'] for i in mod.match.to_jsondict()['OFPMatch']["oxm_fields"] }
			flow_mod = {'type': 'FLOWMOD', 'timestamp': timestamp, 'datapath_id': datapath.id,
												'match':match_obj, 'cookie': mod.cookie, 'command': mod.command, 'flags': mod.flags,
												'idle_timeout': mod.idle_timeout, 'hard_timeout': mod.hard_timeout,
												'priority': mod.priority, 'buffer_id': mod.buffer_id, 'out_port': mod.out_port}
			flow_list.append(flow_mod)
			datapath.send_msg(mod)
			# get the switch from switch_list from corresponding datapath_id, increment flow_mod, update the flow table
			switch = self.switch_list[datapath.id]
			flow = datamodel.FlowMod(datapath_id=datapath.id, timestamp=timestamp, match=mod.match, command=mod.command, flags=mod.flags, idle_timeout=mod.idle_timeout, hard_timeout=mod.hard_timeout,
							 priority=mod.priority, buffer_id = mod.buffer_id, out_port = mod.out_port, cookie=mod.cookie)
			switch.update_flow_table(flow_mod, switch_class.FLOW_OPERATION.ADD)
			#switch.update_flow_table({k: v for k, v in flow_mod.items() if k != 'type'}, switch_class.FLOW_OPERATION.ADD)

	# writing logs
	def write_to_csv(self):
			global batch_number, flow_list
			write_logs(batch_number, flow_list)

	# When switch features comes to the controller (it comes when there is a new switch), a first flow append to the table
	# We also append this to our flow_list to follow them
	def add_flow(self, datapath, timestamp, priority, match, actions, buffer_id=None):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
		mod = None
		if buffer_id:
			mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id, flags=ofproto.OFPFF_SEND_FLOW_REM, priority=priority, match=match, instructions=inst)
		else:
			mod = parser.OFPFlowMod(datapath=datapath, priority=priority, flags=ofproto.OFPFF_SEND_FLOW_REM, match=match, instructions=inst)
		match_obj = {i['OXMTlv']['field']: i['OXMTlv']['value'] for i in mod.match.to_jsondict()['OFPMatch']["oxm_fields"] }
		flow_mod = {'type': 'FLOWMOD', 'timestamp': timestamp, 'datapath_id': datapath.id, 'match': match_obj, 'cookie': mod.cookie, 'command': mod.command, 'flags': mod.flags, 'idle_timeout': mod.idle_timeout, 'hard_timeout': mod.hard_timeout, 'priority': mod.priority, 'buffer_id': mod.buffer_id, 'out_port': mod.out_port }
		flow_list.append(flow_mod)
		switch = self.switch_list[datapath.id]
		flow = datamodel.FlowMod(datapath_id=datapath.id, timestamp=timestamp, match=match, command=mod.command, flags=mod.flags, idle_timeout=mod.idle_timeout, hard_timeout=mod.hard_timeout,
							 priority=mod.priority, buffer_id = mod.buffer_id, out_port = mod.out_port, cookie=mod.cookie)
		# switch.update_flow_table(flow_mod, switch_class.FLOW_OPERATION.ADD)
		datapath.send_msg(mod)

	# When packet_in async messages comes from switch to the controller, it will trigger this function
	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def _packet_in_handler(self, ev):
		global flow_list
		if ev.msg.msg_len < ev.msg.total_len:
			self.logger.debug("packet truncated: only %s of %s bytes", ev.msg.msg_len, ev.msg.total_len)
		msg = ev.msg
		timestamp = ev.timestamp
		datapath = msg.datapath
		datapath_id = datapath.id
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		in_port = msg.match['in_port']
		data = msg.data

		if msg.reason == ofproto.OFPR_NO_MATCH:
			reason = 'NO MATCH'
		elif msg.reason == ofproto.OFPR_ACTION:
			reason = 'ACTION'
		elif msg.reason == ofproto.OFPR_INVALID_TTL:
			reason = 'INVALID TTL'
		else:
			reason = 'unknown'

		
		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocols(ethernet.ethernet)[0]

		# add this to our csv file and increment packet_in count
		flow_list.append({'type': 'PACKETIN', 'timestamp': timestamp, 'datapath_id': datapath_id, 'in_port': in_port, 'reason': reason, 'eth_src': eth.src, 'eth_dst': eth.dst})
		switch = self.switch_list[datapath_id]
		switch.n_packet_in += 1
		# we should add this also the switch's packet_ins as:
		# packet_in_flow = {'type': 'PACKETIN', 'timestamp': timestamp, 'datapath_id': datapath_id, 'in_port': in_port, 'reason': reason, 'eth_src': eth.src, 'eth_dst': eth.dst}
		#flow_list.append(packet_in_flow)
		#switch.packet_ins.append(packet_in_flow)

		if eth.ethertype == ether_types.ETH_TYPE_LLDP:
			return
		dst = eth.dst
		src = eth.src
		dpid = format(datapath.id, "d").zfill(16)
  
		self.mac_to_port.setdefault(dpid, {})
		self.mac_to_port[dpid][src] = in_port

		# if destionation mac has port before out_port should be this, else append new from ofproto
		if dst in self.mac_to_port[dpid]:
			out_port = self.mac_to_port[dpid][dst]
		else:
			out_port = ofproto.OFPP_FLOOD
		actions = [parser.OFPActionOutput(out_port)]

		# when outport was defined before ? 
		# install a flow to avoid packet_in next time
		if out_port != ofproto.OFPP_FLOOD:
			# get its protocol, and arranging match w.r.t its protocol (tcp, udp, icmp)
			if eth.ethertype == ether_types.ETH_TYPE_IP:
				ip = pkt.get_protocol(ipv4.ipv4)
				srcip = ip.src
				dstip = ip.dst
				protocol = ip.proto
				if protocol == in_proto.IPPROTO_ICMP:
					t = pkt.get_protocol(icmp.icmp)
					match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=srcip, ipv4_dst=dstip, ip_proto=protocol, icmpv4_code=t.code, icmpv4_type=t.type)		
				elif protocol == in_proto.IPPROTO_TCP:
					t = pkt.get_protocol(tcp.tcp)
					match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=srcip, ipv4_dst=dstip, ip_proto=protocol, tcp_src=t.src_port, tcp_dst=t.dst_port,)
				elif protocol == in_proto.IPPROTO_UDP:
					u = pkt.get_protocol(udp.udp)
					match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=srcip, ipv4_dst=dstip, ip_proto=protocol, udp_src=u.src_port, udp_dst=u.dst_port,)

				if msg.buffer_id != ofproto.OFP_NO_BUFFER:
					self.logger.info(datapath)
					self.send_flow_mod(datapath, timestamp, match, actions, 1, msg.buffer_id)
					return
				else:
					self.send_flow_mod(datapath, timestamp, match, actions, 1)
		data = None
		if msg.buffer_id == ofproto.OFP_NO_BUFFER:
			data = msg.data
		out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=data)
		datapath.send_msg(out)

	# this function will trigger whenever controller sends it will remove the flow with a reason
	@set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
	def flow_removed_handler(self, ev):
		global flow_list
		msg = ev.msg
		dp = msg.datapath
		ofp = dp.ofproto
		timestamp = ev.timestamp
		datapath_id = dp.id
		match = msg.match
		
		cookie = msg.cookie
		priority = msg.priority
		duration_sec = msg.duration_sec
		duration_nsec = msg.duration_nsec
		idle_timeout = msg.idle_timeout
		packet_count = msg.packet_count
		byte_count = msg.byte_count
		self.write_to_csv()
		if msg.reason == ofp.OFPRR_IDLE_TIMEOUT:
			reason = 'IDLE TIMEOUT'
		elif msg.reason == ofp.OFPRR_HARD_TIMEOUT:
			reason = 'HARD TIMEOUT'
		elif msg.reason == ofp.OFPRR_DELETE:
			reason = 'DELETE'
		elif msg.reason == ofp.OFPRR_GROUP_DELETE:
			reason = 'GROUP DELETE'
		else:
			reason = 'unknown'
		# TODO check occupance rate of switch
		# add this message into csv, increase n_removed_flows, update the flow table and add flow_removed to this flow
		match_obj = {i['OXMTlv']['field']: i['OXMTlv']['value'] for i in match.to_jsondict()['OFPMatch']["oxm_fields"] }
		flow_removed_details = {'type': 'FLOWREMOVED', 'timestamp': timestamp, 'datapath_id': datapath_id, 'match': match_obj, 'cookie': cookie, 'priority': priority,'duration_sec': duration_sec, 'duration_nsec': duration_nsec, 'idle_timeout': idle_timeout, 'packet_count': packet_count, 'byte_count': byte_count, 'reason': reason}
		flow_list.append(flow_removed_details)
		switch = self.switch_list[datapath_id]	
		removed_flow = datamodel.FlowRemoved(datapath_id=datapath_id, timestamp=timestamp, match=match, idle_timeout=idle_timeout, 
										 duration_sec=duration_sec,duration_nsec=duration_nsec, packet_count=packet_count,
										 byte_count=byte_count, reason= reason, cookie=cookie, priority=priority)			   
		switch.update_flow_table(flow_removed_details, switch_class.FLOW_OPERATION.DELETE)

	# This function will trigger whenever an error messages comes into the controller
	@set_ev_cls(ofp_event.EventOFPErrorMsg, [HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER, MAIN_DISPATCHER])
	def error_msg_handler(self, ev):
		global flow_list
		msg = ev.msg
		dp = msg.datapath
		error_code = msg.code
		error_data = msg.data
		if msg.type == dp.ofproto.OFPET_HELLO_FAILED:
			reason = 'OFPET_HELLO_FAILED'
		elif msg.type == dp.ofproto.OFPET_BAD_REQUEST:
			reason = 'OFPET_BAD_REQUEST'
		elif msg.type == dp.ofproto.OFPET_BAD_ACTION:
			reason = 'OFPET_BAD_ACTION'
		elif msg.type == dp.ofproto.OFPET_FLOW_MOD_FAILED: #TODO add update thresholds function
			reason = 'OFPET_FLOW_MOD_FAILED'
		elif msg.type == dp.ofproto.OFPET_PORT_MOD_FAILED:
			reason = 'OFPET_PORT_MOD_FAILED'
		else:
			reason = 'OFPET_QUEUE_OP_FAILED'
		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocols(ethernet.ethernet)[0]
		switch = self.switch_list[dp.id]
		switch.n_errors+=1
		flow_list.append({'type': 'ERROR', 'timestamp': ev.timestamp, 'datapath_id': dp.id, 'reason': reason, 'eth_src': eth.src, 'eth_dst': eth.dst, "data": error_data, "error_code": error_code})

	# this will trigger when EventOFPStatsReply comes? 
	"""
	@set_ev_cls(ofp_event.EventOFPStatsReply, MAIN_DISPATCHER)
	def stats_reply_handler(self, ev):
		print("stats_reply_handler")
		msg = ev.msg
		ofp = msg.datapath.ofproto
		body = ev.msg.body

		if msg.type == ofp.OFPST_FLOW:
			self.flow_stats_reply_handler(body)

	
	
	@set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
	def flow_stats_reply_handler(self, ev):
		
		flows = []
		for stat in ev.msg.body:
			flows.append('table_id=%s '
						'duration_sec=%d duration_nsec=%d '
						'priority=%d '
						'idle_timeout=%d hard_timeout=%d flags=0x%04x '
						'cookie=%d packet_count=%d byte_count=%d '
						'match=%s instructions=%s' %
						(stat.table_id,
						stat.duration_sec, stat.duration_nsec,
						stat.priority,
						stat.idle_timeout, stat.hard_timeout, stat.flags,
						stat.cookie, stat.packet_count, stat.byte_count,
						stat.match, stat.instructions))
		self.logger.debug('FlowStats: %s', flows)
	"""

	@set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
	def _flow_stats_reply_handler(self, ev):
		print("flow_stats_reply_handler")
		timestamp = datetime.now()
		timestamp = timestamp.timestamp()
		file0 = open("PredictFlowStatsfile.csv","w")
		file0.write('timestamp,datapath_id,flow_id,ip_src,tp_src,ip_dst,tp_dst,ip_proto,icmp_code,icmp_type,flow_duration_sec,flow_duration_nsec,idle_timeout,hard_timeout,flags,packet_count,byte_count,packet_count_per_second,packet_count_per_nsecond,byte_count_per_second,byte_count_per_nsecond,byte_per_packet\n')
		flow_stats = []
		body = ev.msg.body
		icmp_code = -1
		icmp_type = -1
		tp_src = 0
		tp_dst = 0
		for stat in sorted([flow for flow in body if (flow.priority == 1) ], key=lambda flow:
						(flow.match['eth_type'],flow.match['ipv4_src'],flow.match['ipv4_dst'],flow.match['ip_proto'])):
			ip_src = stat.match['ipv4_src']
			ip_dst = stat.match['ipv4_dst']
			ip_proto = stat.match['ip_proto']

			if stat.match['ip_proto'] == 1:
				icmp_code = stat.match['icmpv4_code']
				icmp_type = stat.match['icmpv4_type']
			elif stat.match['ip_proto'] == 6:
				tp_src = stat.match['tcp_src']
				tp_dst = stat.match['tcp_dst']
			elif stat.match['ip_proto'] == 17:
				tp_src = stat.match['udp_src']
				tp_dst = stat.match['udp_dst']
			flow_id = str(ip_src) + str(tp_src) + str(ip_dst) + str(tp_dst) + str(ip_proto)
			try:
				packet_count_per_second = stat.packet_count/stat.duration_sec
				packet_count_per_nsecond = stat.packet_count/stat.duration_nsec
			except:
				packet_count_per_second = 0
				packet_count_per_nsecond = 0
			
			try:
				byte_count_per_second = stat.byte_count/stat.duration_sec
				byte_count_per_nsecond = stat.byte_count/stat.duration_nsec
			except:
				byte_count_per_second = 0
				byte_count_per_nsecond = 0

			try:
				byte_per_packet = stat.byte_count/stat.packet_count
			except:
				byte_per_packet = 0
			
			file0.write("{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n"
								.format(timestamp, ev.msg.datapath.id, flow_id, ip_src, tp_src,ip_dst, tp_dst,
												stat.match['ip_proto'],icmp_code,icmp_type,
												stat.duration_sec, stat.duration_nsec,
												stat.idle_timeout, stat.hard_timeout,
												stat.flags, stat.packet_count,stat.byte_count,
												packet_count_per_second,packet_count_per_nsecond,
												byte_count_per_second,byte_count_per_nsecond,byte_per_packet))
			stat = {'timestamp': timestamp, 'datapath_id':ev.msg.datapath.id, 'duration':stat.duration_sec, 'packet_count_per_second': packet_count_per_second, 'byte_count_per_second': byte_count_per_second, 'byte_per_packet':byte_per_packet,
			 'ip_proto': ip_proto, 'ip_src':ip_src, 'ip_dst': ip_dst, 'tp_src':tp_src, 'tp_dst':tp_dst, 'icmp_code': icmp_code, 'icmp_type':icmp_type
			 }
			# TODO need to send w.r.t datapath_id
			print("Stat: ")
			print(stat)
			flow_stats.append(stat)
			

		switch = self.switch_list[ev.msg.datapath.id]
		switch.get_stats(flow_stats)
		file0.close()
						
	# this will send flow stats request to the switches (it will used in getting requests at detection)
	def send_flow_stats_request(self, datapath):
		print("send_flow_stats_request")
		ofp = datapath.ofproto
		ofp_parser = datapath.ofproto_parser

		cookie = cookie_mask = 0
		match = ofp_parser.OFPMatch(in_port=1)
		req = ofp_parser.OFPFlowStatsRequest(datapath, 0,
											ofp.OFPTT_ALL,
											ofp.OFPP_ANY, ofp.OFPG_ANY,
											cookie, cookie_mask,
											match)
		datapath.send_msg(req)

	# this will send aggregate stats request to the switches (they will response as the sum of their flow tables)
	def send_aggregate_stats_request(self, datapath):
		ofp = datapath.ofproto
		ofp_parser = datapath.ofproto_parser

		cookie = cookie_mask = 0
		match = ofp_parser.OFPMatch(in_port=1)
		req = ofp_parser.OFPAggregateStatsRequest(datapath, 0,
												ofp.OFPTT_ALL,
												ofp.OFPP_ANY,
												ofp.OFPG_ANY,
												cookie, cookie_mask,
												match)
		datapath.send_msg(req)

	# when responses comes from switches after sending flow stats request, this function will be triggered
	# we should use it to whether our flow_count and real flow count is match by calling it in 20 sec i.e.
	@set_ev_cls(ofp_event.EventOFPAggregateStatsReply, MAIN_DISPATCHER)
	def aggregate_stats_reply_handler(self, ev):
		"""{
		"OFPAggregateStatsReply": {
			"body": {
				"OFPAggregateStats": {
					"byte_count": 574, 
					"flow_count": 6, 
					"packet_count": 7
				}
			}, 
			"flags": 0, 
			"type": 2
		}
		}"""
		body = ev.msg.body

		self.logger.debug('AggregateStats: packet_count=%d byte_count=%d '
						'flow_count=%d',
						body.packet_count, body.byte_count,
						body.flow_count)
	
	"""
	from https://github.com/chiragbiradar/DDoS-Attack-Detection-and-Mitigation/blob/main/Codes/controller/controller.py
	@set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
		def _flow_stats_reply_handler(self, ev):

				timestamp = datetime.now()
				timestamp = timestamp.timestamp()

				file0 = open("PredictFlowStatsfile.csv","w")
				file0.write('timestamp,datapath_id,flow_id,ip_src,tp_src,ip_dst,tp_dst,ip_proto,icmp_code,icmp_type,flow_duration_sec,flow_duration_nsec,idle_timeout,hard_timeout,flags,packet_count,byte_count,packet_count_per_second,packet_count_per_nsecond,byte_count_per_second,byte_count_per_nsecond\n')
				body = ev.msg.body
				icmp_code = -1
				icmp_type = -1
				tp_src = 0
				tp_dst = 0

				for stat in sorted([flow for flow in body if (flow.priority == 1) ], key=lambda flow:
						(flow.match['eth_type'],flow.match['ipv4_src'],flow.match['ipv4_dst'],flow.match['ip_proto'])):
				
						ip_src = stat.match['ipv4_src']
						ip_dst = stat.match['ipv4_dst']
						ip_proto = stat.match['ip_proto']
						
						if stat.match['ip_proto'] == 1:
								icmp_code = stat.match['icmpv4_code']
								icmp_type = stat.match['icmpv4_type']
								
						elif stat.match['ip_proto'] == 6:
								tp_src = stat.match['tcp_src']
								tp_dst = stat.match['tcp_dst']

						elif stat.match['ip_proto'] == 17:
								tp_src = stat.match['udp_src']
								tp_dst = stat.match['udp_dst']

						flow_id = str(ip_src) + str(tp_src) + str(ip_dst) + str(tp_dst) + str(ip_proto)
					
						try:
								packet_count_per_second = stat.packet_count/stat.duration_sec
								packet_count_per_nsecond = stat.packet_count/stat.duration_nsec
						except:
								packet_count_per_second = 0
								packet_count_per_nsecond = 0
								
						try:
								byte_count_per_second = stat.byte_count/stat.duration_sec
								byte_count_per_nsecond = stat.byte_count/stat.duration_nsec
						except:
								byte_count_per_second = 0
								byte_count_per_nsecond = 0
								
						file0.write("{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n"
								.format(timestamp, ev.msg.datapath.id, flow_id, ip_src, tp_src,ip_dst, tp_dst,
												stat.match['ip_proto'],icmp_code,icmp_type,
												stat.duration_sec, stat.duration_nsec,
												stat.idle_timeout, stat.hard_timeout,
												stat.flags, stat.packet_count,stat.byte_count,
												packet_count_per_second,packet_count_per_nsecond,
												byte_count_per_second,byte_count_per_nsecond))
						
				file0.close()
	"""
