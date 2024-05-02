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

import switch_class

import schedule
import csv
flow_list = []

batch_number = 0

def write_logs(batch_number, logs):
    filename = f"log_batch_{batch_number}.txt"
    with open(filename, mode='w') as file:
        for log in logs:

            file.write(str(log) + '\n')

class SimpleSwitch13(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

	def __init__(self, *args, **kwargs):
			super(SimpleSwitch13, self).__init__(*args, **kwargs)
			self.mac_to_port = {}
			self.switch_list = {}

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

			switch = switch_class.Switch(
					timestamp, datapath_id, n_buffers, n_tables, capabilities)
			self.switch_list[datapath_id] = switch

			flow_list.append({'type': 'SwitchFeatures', 'timestamp': timestamp, 'datapath_id': datapath_id,
												'n_buffers': n_buffers, 'n_tables': n_tables, 'capabilities': capabilities})

			match = parser.OFPMatch()
			actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
																				ofproto.OFPCML_NO_BUFFER)]
			self.add_flow(datapath, timestamp, 0, match, actions)

	def send_flow_mod(self, datapath, timestamp, match, actions, priority, buffer_id=None):
			ofp = datapath.ofproto
			ofp_parser = datapath.ofproto_parser
			idle_timeout = 10
			inst = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
			mod = None
			if (buffer_id):
				mod = ofp_parser.OFPFlowMod(datapath, cookie=0, cookie_mask=0, table_id=0, command=ofp.OFPFC_ADD,
																		idle_timeout=idle_timeout, hard_timeout=0,priority=priority, buffer_id=buffer_id,
																		out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY, flags=ofp.OFPFF_SEND_FLOW_REM,
																		match=match, instructions=inst)
			else:
				mod = ofp_parser.OFPFlowMod(datapath, cookie=0, cookie_mask=0, table_id=0, command=ofp.OFPFC_ADD, idle_timeout=idle_timeout, hard_timeout=0,
																		priority=priority, out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
																		flags=ofp.OFPFF_SEND_FLOW_REM, match=match, instructions=inst)
    					
			flow_mod = {'type': 'FLOWMOD', 'timestamp': timestamp, 'datapath_id': datapath.id,
												'match': mod.match, 'cookie': mod.cookie, 'command': mod.command, 'flags': mod.flags,
												'idle_timeout': mod.idle_timeout, 'hard_timeout': mod.hard_timeout,
												'priority': mod.priority, 'buffer_id': mod.buffer_id, 'out_port': mod.out_port}
			datapath.send_msg(mod)
			switch = self.switch_list[datapath.id]
			# switch.flow_mods += 1
			# switch.update_flow_table({k: v for k, v in flow_mod.items() if k != 'type'}, switch_class.FLOW_OPERATION.ADD)

	def write_to_csv(self):
			global batch_number, flow_list
			write_logs(batch_number, flow_list)

	def add_flow(self, datapath, timestamp, priority, match, actions, buffer_id=None):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
		mod = None
		if buffer_id:
			mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id, flags=ofproto.OFPFF_SEND_FLOW_REM, priority=priority, match=match, instructions=inst)
		else:
			mod = parser.OFPFlowMod(datapath=datapath, priority=priority, flags=ofproto.OFPFF_SEND_FLOW_REM, match=match, instructions=inst)
		flow_mod = {'type': 'FLOWMOD', 'timestamp': timestamp, 'datapath_id': datapath.id, 'match': mod.match, 'cookie': mod.cookie, 'command': mod.command, 'flags': mod.flags, 'idle_timeout': mod.idle_timeout, 'hard_timeout': mod.hard_timeout, 'priority': mod.priority, 'buffer_id': mod.buffer_id, 'out_port': mod.out_port }
		flow_list.append(flow_mod)
		switch = self.switch_list[datapath.id]
		switch.flow_mods += 1
		switch.update_flow_table({k: v for k, v in flow_mod.items() if k != 'type'}, switch_class.FLOW_OPERATION.ADD)
		datapath.send_msg(mod)

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
		flow_list.append({'type': 'PACKETIN', 'timestamp': timestamp, 'datapath_id': datapath_id, 'in_port': in_port, 'reason': reason, 'eth_src': eth.src, 'eth_dst': eth.dst})
		switch = self.switch_list[datapath_id]
		switch.n_packet_in += 1

		if eth.ethertype == ether_types.ETH_TYPE_LLDP:
			return
		dst = eth.dst
		src = eth.src
		dpid = format(datapath.id, "d").zfill(16)

		self.mac_to_port.setdefault(dpid, {})
		self.mac_to_port[dpid][src] = in_port

		if dst in self.mac_to_port[dpid]:
			out_port = self.mac_to_port[dpid][dst]
		else:
			out_port = ofproto.OFPP_FLOOD
		actions = [parser.OFPActionOutput(out_port)]
		# install a flow to avoid packet_in next time
		if out_port != ofproto.OFPP_FLOOD:
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
		flow_removed_details = {'type': 'FLOWREMOVED', 'timestamp': timestamp, 'datapath_id': datapath_id, 'match': match, 'cookie': cookie, 'priority': priority,'duration_sec': duration_sec, 'duration_nsec': duration_nsec, 'idle_timeout': idle_timeout, 'packet_count': packet_count, 'byte_count': byte_count, 'reason': reason}
		flow_list.append(flow_removed_details)
		switch = self.switch_list[datapath_id]
		switch.n_flow_removed += 1
		switch.update_flow_table({k: v for k, v in flow_removed_details.items() if k != 'type'}, switch_class.FLOW_OPERATION.ADD)
		switch.flow_removed.append({k: v for k, v in flow_removed_details.items() if k != 'type'})

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
		elif msg.type == dp.ofproto.OFPET_FLOW_MOD_FAILED:
			reason = 'OFPET_FLOW_MOD_FAILED'
		elif msg.type == dp.ofproto.OFPET_PORT_MOD_FAILED:
			reason = 'OFPET_PORT_MOD_FAILED'
		else:
			reason = 'OFPET_QUEUE_OP_FAILED'
		pkt = packet.Packet(msg.data)
		eth = pkt.get_protocols(ethernet.ethernet)[0]
		flow_list.append({'type': 'ERROR', 'timestamp': ev.timestamp, 'datapath_id': dp.id, 'reason': reason, 'eth_src': eth.src, 'eth_dst': eth.dst, "data": error_data, "error_code": error_code})

	@set_ev_cls(ofp_event.EventOFPStatsReply, MAIN_DISPATCHER)
	def stats_reply_handler(self, ev):
		msg = ev.msg
		ofp = msg.datapath.ofproto
		body = ev.msg.body

		if msg.type == ofp.OFPST_FLOW:
			self.flow_stats_reply_handler(body)

	def flow_stats_reply_handler(self, body):
		flows = []
		for stat in body:
				flows.append('table_id=%s '
											'duration_sec=%d duration_nsec=%d '
											'priority=%d '
											'idle_timeout=%d hard_timeout=%d '
											'cookie=%d packet_count=%d byte_count=%d '
											'match=%s instructions=%s' %
											(stat.table_id,
											stat.duration_sec, stat.duration_nsec,
											stat.priority,
											stat.idle_timeout, stat.hard_timeout,
											stat.cookie, stat.packet_count, stat.byte_count,
											stat.match, stat.instructions))
		self.logger.debug('FlowStats: %s', flows)