from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, HANDSHAKE_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, ipv4, tcp, udp, icmp, in_proto
from ryu.lib.packet import ether_types
from ryu import utils
from datetime import datetime
from parameters import IDLE_TIMEOUT, BAN_TIMEOUT
import switch_class

flow_list = []
batch_number = 0
flow_number = -1

# writing logs into the file w.r.t batch number after that it will convert it to csv in analyzer class
def write_logs(batch_number, logs):
		filename = f"log_batch_{batch_number}.txt"
		with open(filename, mode='w') as file:
				for log in logs:
						file.write(str(log) + '\n')

def get_flow_number():
	global flow_number
	flow_number += 1 
	return flow_number
	
def format_match(match):
	return {i['OXMTlv']['field']: i['OXMTlv']['value'] for i in match.to_jsondict()['OFPMatch']["oxm_fields"] }

# a simple switch class from OpenFlow 1.3 documentation (https://github.com/faucetsdn/ryu/blob/master/ryu/app/simple_switch_13.py)
class SimpleSwitch13(app_manager.RyuApp):
	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
	banned_list = []
	white_list = []

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
			idle_timeout = IDLE_TIMEOUT
			inst = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
			mod = None
			cookie_num = get_flow_number()
			#in_port = match['in_port'] doesn't work because of L4 we need to consider
			if (buffer_id):
				mod = ofp_parser.OFPFlowMod(datapath, cookie=cookie_num,cookie_mask=0xFFFFFFFFFFFFFFFF, table_id=0, command=ofp.OFPFC_ADD,
																		idle_timeout=idle_timeout, hard_timeout=0,priority=priority, buffer_id=buffer_id,
																		out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY, flags=ofp.OFPFF_SEND_FLOW_REM,
																		match=match, instructions=inst)
			else:
				mod = ofp_parser.OFPFlowMod(datapath, cookie=cookie_num, cookie_mask=0xFFFFFFFFFFFFFFFF, table_id=0, command=ofp.OFPFC_ADD, idle_timeout=idle_timeout, hard_timeout=0,
																		priority=priority, out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
																		flags=ofp.OFPFF_SEND_FLOW_REM, match=match, instructions=inst)
				
			# Check for TCP/IP with SYN flag (hping3)
			if match.get('ip_proto') == ofproto_v1_3.OFPHTN_IP and match.get('tcp_flags') & ofproto_v1_3.TCP_SYN:
				print("TCP/IP SYN packet detected (likely hping3)")

			# Check for UDP (iperf)
			elif match.get('ip_proto') == ofproto_v1_3.OFPHTN_UDP:
				print("UDP packet detected (likely iperf)")
			
			is_attack = False
			flow_mod = {'type': 'FLOWMOD', 'timestamp': timestamp, 'datapath_id': datapath.id,
												'match':format_match(mod.match), 'cookie': mod.cookie, 'command': mod.command, 'flags': mod.flags,
												'idle_timeout': mod.idle_timeout, 'hard_timeout': mod.hard_timeout,
												'priority': mod.priority, 'buffer_id': mod.buffer_id, 'out_port': mod.out_port, 'is_attack': is_attack}
			flow_list.append(flow_mod)
			datapath.send_msg(mod)
			# get the switch from switch_list from corresponding datapath_id, increment flow_mod, update the flow table
			switch = self.switch_list[datapath.id]
			switch.update_flow_table(flow_mod, switch_class.FLOW_OPERATION.ADD)
	# writing logs
	def write_to_csv(self):
			global batch_number, flow_list
			write_logs(batch_number, flow_list)

	# When switch features comes to the controller (it comes when there is a new switch), a first flow append to the table
	# We also append this to our flow_list to follow them
	def add_flow(self, datapath, timestamp, priority, match, actions, hard_time=0, buffer_id=None):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
		mod = None
		cookie_num = get_flow_number()
		if buffer_id:
			mod = parser.OFPFlowMod(datapath=datapath, cookie=cookie_num, cookie_mask=0xFFFFFFFFFFFFFFFF, buffer_id=buffer_id, flags=ofproto.OFPFF_SEND_FLOW_REM, priority=priority, match=match, instructions=inst, hard_timeout = hard_time)
		else:
			mod = parser.OFPFlowMod(datapath=datapath, cookie=cookie_num, cookie_mask=0xFFFFFFFFFFFFFFFF, priority=priority, flags=ofproto.OFPFF_SEND_FLOW_REM, match=match, instructions=inst, hard_timeout = hard_time)
		
		flow_mod = {'type': 'FLOWMOD', 'timestamp': timestamp, 'datapath_id': datapath.id, 'match': format_match(mod.match), 'cookie': mod.cookie, 'command': mod.command, 'flags': mod.flags, 'idle_timeout': mod.idle_timeout, 'hard_timeout': mod.hard_timeout, 'priority': mod.priority, 'buffer_id': mod.buffer_id, 'out_port': mod.out_port }
		flow_list.append(flow_mod)
		switch = self.switch_list[datapath.id]
		datapath.send_msg(mod)
	
	## Function adds a empty action that implies the dropping the packets coming from related ip_src
	def block_ip(self, datapath, ip_src):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		timestamp = datetime.now()
		match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=ip_src)
		actions = []
		self.add_flow(datapath, timestamp, 2, match, actions, hard_time=BAN_TIMEOUT) ## Hardtime is really important for blocking range 
	
	def drop_flow(self, datapath, cookie_num):
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		mod = parser.OFPFlowMod(
			datapath=datapath,
			cookie=cookie_num, ## cookie will help to match the flows
			cookie_mask=0xFFFFFFFFFFFFFFFF,
			priority = 2,
			table_id=ofproto.OFPTT_ALL,
			hard_timeout=BAN_TIMEOUT,
			idle_timeout=BAN_TIMEOUT,
			command=ofproto.OFPFC_DELETE,
			out_port=ofproto.OFPP_ANY,
			out_group=ofproto.OFPG_ANY)
		datapath.send_msg(mod)
	
	def add_banned_list(self,flow):
		self.banned_list.append(flow)
  
	def add_white_list(self, flow):
		self.white_list.append(flow)
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
		# self.write_to_csv()
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
		# add this message into csv, increase n_removed_flows, update the flow table and add flow_removed to this flow
		flow_removed_details = {'type': 'FLOWREMOVED', 'timestamp': timestamp, 'datapath_id': datapath_id, 'match': format_match(match), 'cookie': cookie, 'priority': priority,'duration_sec': duration_sec, 'duration_nsec': duration_nsec, 'idle_timeout': idle_timeout, 'packet_count': packet_count, 'byte_count': byte_count, 'reason': reason}
		flow_list.append(flow_removed_details)
		switch = self.switch_list[datapath_id]	   
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
		elif msg.type == dp.ofproto.OFPET_FLOW_MOD_FAILED:
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
