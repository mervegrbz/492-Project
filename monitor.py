from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
import detector
import switch
from datetime import datetime
import pickle,os
import pandas as pd

class SimpleMonitor13(switch.SimpleSwitch13):

		def __init__(self, *args, **kwargs):

				super(SimpleMonitor13, self).__init__(*args, **kwargs)
				self.datapaths = {}
				self.monitor_thread = hub.spawn(self._monitor)

		@set_ev_cls(ofp_event.EventOFPStateChange,
								[MAIN_DISPATCHER, DEAD_DISPATCHER])
		def _state_change_handler(self, ev):
				datapath = ev.datapath
				if ev.state == MAIN_DISPATCHER:
						if datapath.id not in self.datapaths:
								self.logger.debug('register datapath: %016x', datapath.id)
								self.datapaths[datapath.id] = datapath
				elif ev.state == DEAD_DISPATCHER:
						if datapath.id in self.datapaths:
								self.logger.debug('unregister datapath: %016x', datapath.id)
								del self.datapaths[datapath.id]

		def _monitor(self):
			while True:
				if detector.LOW_RATE_FLAG:
					for dp in self.datapaths.values():
						self._request_stats(dp)
						detector.LOW_RATE_FLAG = False
				if detector.HIGH_RATE_FLAG:
					for dp in self.datapaths.values():
						self._request_stats(dp)
						detector.LOW_RATE_FLAG = False
				hub.sleep(5)


		def _request_stats(self, datapath):
				self.logger.debug('send stats request: %016x', datapath.id)
				parser = datapath.ofproto_parser

				req = parser.OFPFlowStatsRequest(datapath)
				datapath.send_msg(req)

		@set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
		def _flow_stats_reply_handler(self, ev):
				timestamp = datetime.now()
				body = ev.msg.body
				datapath = ev.msg.datapath
				icmp_code = -1
				icmp_type = -1
				tp_src = 0
				tp_dst = 0
				flow_list = []
				for stat in body:
					switch.format_match(stat.match)
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
					
				

					packet_count_per_second = stat.packet_count/stat.duration_sec if stat.duration_sec != 0 else 0
					byte_count_per_second = stat.byte_count/stat.duration_sec if stat.duration_sec != 0 else 0
					flow_list.append([ip_src,packet_count_per_second,byte_count_per_second, stat.cookie])
			
				switch = self.switch_list[ev.msg.datapath.id]
				# switch has the history batches of flow statistics get the related columns and compare it with current flow to understand whether it is suspected or not
				related_batch = switch.get_related_batch(num_of_batch=5)
				columns = ['timestamp', 'capacity_used', 'removed_flow_average_duration', 'removed_flow_byte_per_packet',
						 'average_flow_duration_on_table', 'packet_in_mean', 'packet_in_std_dev', 'number_of_errors'
						 'flow_table_stats', 'removed_table_stats']
				removed_flow_average_duration = related_batch['removed_flow_average_duration'].mean()
				removed_flow_byte_per_packet = related_batch['removed_flow_byte_per_packet'].mean()
				
				for flow in flow_list:
						if flow[1] < 0.8 * removed_flow_byte_per_packet and flow[2] > 0.8 * removed_flow_average_duration:
								self.add_banned_list(flow)
								self.drop_flow(datapath, flow[3])
								self.block_ip(datapath, flow[0] )

						if flow[1] > 2 * removed_flow_byte_per_packet: 
								## TODO protect the whitelisted flows from being banned
								self.add_white_list(flow)
				## removed_flow_average_duration,removed_flow_byte_per_packet,average_flow_duration_on_table can be used to detect whether the flow is suspected or not
				
				
				
						
						
						
						 
						
