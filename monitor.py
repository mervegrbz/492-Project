from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
import predictor
import controller
from datetime import datetime
import pickle,os
import pandas as pd
from parameters import *
from flow_inspector import ml_flow
from detector import flow_labeller
class SimpleMonitor13(controller.SimpleSwitch13):

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
## TODO remove flowlar uzerinden ML calistirip kac tane flowun suspected oldugunu bulup sonrasinda stat cekmek daha mantikli olabilir
## Eger remove flowlarda suspected var ise stat cekmek mantikli olabilir

		def _monitor(self):
			while True:
				if predictor.LOW_RATE_FLAG:
					for dp in self.datapaths.values():
						## TODO eger capacity cok yuksek degilse mitigation icin 3 stat daha beklenir burada capacity kontrol bir daha yapalim stat atmadan once eger azsa biraz bekleyelim
						self._request_stats(dp)
						predictor.LOW_RATE_FLAG = False
				if predictor.HIGH_RATE_FLAG:
					for dp in self.datapaths.values():
						# TODO no need to request stats in high rate, at first drop the newly appended flows
						self._request_stats(dp)
						predictor.LOW_RATE_FLAG = False
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
				## store the flows in the body in a dataframe
				flow_rules = pd.DataFrame(columns=['ipv4_src','ipv4_dst','port_src','port_dst','ip_proto', 'cookie', 'duration_sec', 'byte_count', 'packet_count'])
    
				for stat in body:

					match = controller.format_match(stat.match)
					if ( match == {} or 'ip_proto' not in  match ):
			 				continue
					ip_src = match['ipv4_src']
					ip_dst = match['ipv4_dst']
					ip_proto = match['ip_proto'] 
					if stat.match['ip_proto'] == 1:
							icmp_code =match['icmpv4_code']
							icmp_type = match['icmpv4_type'] 
					elif stat.match['ip_proto'] == 6:
							tp_src = match['tcp_src']
							tp_dst = match['tcp_dst']
					elif stat.match['ip_proto'] == 17:
							tp_src = match['udp_src']
							tp_dst = match['udp_dst']
					row = pd.Series([ip_src, ip_dst, tp_src, tp_dst, ip_proto, stat.cookie, stat.duration_sec, stat.byte_count, stat.packet_count], index=flow_rules.columns)
					flow_rules = flow_rules.append(row, ignore_index=True)

				flow_rules = ml_flow(flow_rules)
				## get the suspected flows
				# flow_rules = flow_labeller(flow_rules)
				# suspected_flows = flow_rules[flow_rules['label'] == 1]
				switch = self.switch_list[ev.msg.datapath.id]
				# switch has the history batches of flow statistics get the related columns and compare it with current flow to understand whether it is suspected or not
				related_batch = switch.get_related_batch(num_of_batch=5)
				
				removed_flow_average_duration = related_batch['removed_flow_average_duration'].mean()
				removed_flow_byte_per_packet = related_batch['removed_flow_byte_per_packet'].mean() # the second important feature to distunguish mice and elephant
				removed_average_byte_per_sec = related_batch['removed_average_byte_per_sec'].mean() # the most important to distunguish
				
    
				for index, flow in flow_rules.iterrows():
					if flow['bps'] < BYTE_PER_SEC_BLACK_LIST * removed_average_byte_per_sec and flow['bpp'] < BYTE_PER_PACKET_BLACK_LIST * removed_flow_byte_per_packet:
						self.add_banned_list(flow)
						self.drop_flow(datapath, flow['cookie'])
						self.block_ip(datapath, flow['ipv4_src'] )
					if flow['bps'] > 2 * removed_average_byte_per_sec:
						self.add_white_list(flow)
				
				
				
						
						
						
						 
						
