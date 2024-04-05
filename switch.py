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
import time
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, HANDSHAKE_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu import utils

import schedule
import csv
flow_list = []
batch_number = 0


def write_logs(batch_number, logs):
    filename = f"log_batch_{batch_number}.txt"
    with open(filename, mode='w') as file:
        for log in logs:
            file.write(str(log)+ '\n')

def write_file(logs):
    filename = "logger.txt"
    with open(filename, mode='w') as file:
        for log in logs:
            file.write(str(log))

    
class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
       

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
        
        
        # add all datapath info to the flow_list
        # log details 

        flow_list.append({'type':'SwitchFeatures','timestamp': timestamp, 'datapath_id': datapath_id,
                          'n_buffers': n_buffers, 'n_tables': n_tables,
                          'capabilities': capabilities})
        #write_file({'type':'SwitchFeatures','timestamp': timestamp, 'datapath_id': datapath_id,'n_buffers': n_buffers, 'n_tables': n_tables,'capabilities': capabilities})
        self.write_to_csv()

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, timestamp, 0, match, actions)

    def send_flow_mod(self, datapath, timestamp, priority, match, actions, buffer_id=None):
      ofp = datapath.ofproto
      ofp_parser = datapath.ofproto_parser

      idle_timeout = 10
      inst = [ofp_parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS,
                                              actions)]
      mod = None
      if (buffer_id):
        mod = ofp_parser.OFPFlowMod(datapath, cookie = 0, cookie_mask=0, table_id=0, command= ofp.OFPFC_ADD,
                                    idle_timeout= idle_timeout, hard_timeout= 0,
                                    priority= priority, buffer_id=  buffer_id,
                                    out_port= ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
                                    flags=ofp.OFPFF_SEND_FLOW_REM,
                                    match= match, instructions=inst)

      else: 

        mod = ofp_parser.OFPFlowMod(datapath, cookie = 0, cookie_mask=0,table_id=0,command= ofp.OFPFC_ADD,
                                    idle_timeout= idle_timeout, hard_timeout= 0,
                                    priority= priority,
                                    out_port= ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
                                    flags=ofp.OFPFF_SEND_FLOW_REM,
                                    match= match, instructions=inst)

      flow_list.append({'type':'FLOWMOD','timestamp': timestamp, 'datapath_id': datapath.id,
                          'match': mod.match, 'cookie': mod.cookie, 'command': mod.command, 'flags': mod.flags,
                          'idle_timeout': mod.idle_timeout, 'hard_timeout': mod.hard_timeout,
                          'priority': mod.priority, 'buffer_id': mod.buffer_id,
                          'out_port': mod.out_port})
      #write_file({'type':'FLOWMOD','timestamp': timestamp, 'datapath_id': datapath.id,'match': mod.match, 'cookie': mod.cookie, 'command': mod.command, 'flags': mod.flags,'idle_timeout': mod.idle_timeout, 'hard_timeout': mod.hard_timeout,'priority': mod.priority, 'buffer_id': mod.buffer_id,'out_port': mod.out_port})
   
                                
      datapath.send_msg(mod)
      self.write_to_csv()
    def write_to_csv(self):
        global batch_number, flow_list
        if len(flow_list)>10:
            write_logs(batch_number, flow_list)
            #write_file(flow_list)
            batch_number += 1
            flow_list = []
    

    def add_flow(self, datapath, timestamp, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser


        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = None
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst) 
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        
        flow_list.append({'type': 'FLOWMOD','timestamp': timestamp, 'datapath_id': datapath.id,
                          'match': mod.match, 'cookie': mod.cookie, 'command': mod.command, 'flags': mod.flags,
                          'idle_timeout': mod.idle_timeout, 'hard_timeout': mod.hard_timeout,
                          'priority': mod.priority, 'buffer_id': mod.buffer_id,
                          'out_port': mod.out_port})
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        global flow_list
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        timestamp = ev.timestamp
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        buffer_id = msg.buffer_id
        data = msg.data
        total_len = msg.total_len

        if msg.reason == ofproto.OFPR_NO_MATCH:
            reason = 'NO MATCH'
        elif msg.reason == ofproto.OFPR_ACTION:
            reason = 'ACTION'
        elif msg.reason == ofproto.OFPR_INVALID_TTL:
            reason = 'INVALID TTL'
        else:
            reason = 'unknown'
        datapath_id = datapath.id


        self.write_to_csv()
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src
        dpid = format(datapath.id, "d").zfill(16)
        
        self.mac_to_port.setdefault(dpid, {})        
        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]
        self.write_to_csv()
        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.logger.info(datapath)
                self.send_flow_mod(datapath, timestamp, 1, match, actions, msg.buffer_id)
                return
            else:
                self.send_flow_mod(datapath, timestamp, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
                          
        flow_list.append({'type':'PACKETIN','timestamp': timestamp,'datapath_id':datapath_id, 'buffer_id': buffer_id, 'data': data, 'in_port': in_port, 'total_len': total_len, 'reason': reason})
        #write_file({'type':'PACKETIN','timestamp': timestamp,'datapath_id':datapath_id, 'buffer_id': buffer_id, 'data': data, 'in_port': in_port, 'total_len': total_len, 'reason': reason})
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
        flow_list.append({'type':'FLOWREMOVED','timestamp': timestamp, 'datapath_id': datapath_id, 'match': match, 'cookie': cookie, 'priority': priority, 'duration_sec': duration_sec, 'duration_nsec': duration_nsec, 'idle_timeout': idle_timeout, 'packet_count': packet_count, 'byte_count': byte_count, 'reason': reason})
        #write_file({'type':'FLOWREMOVED','timestamp': timestamp, 'datapath_id': datapath_id, 'match': match, 'cookie': cookie, 'priority': priority, 'duration_sec': duration_sec, 'duration_nsec': duration_nsec, 'idle_timeout': idle_timeout, 'packet_count': packet_count, 'byte_count': byte_count, 'reason': reason})
        self.write_to_csv()
        
    
    @set_ev_cls(ofp_event.EventOFPErrorMsg,
            [HANDSHAKE_DISPATCHER, CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def error_msg_handler(self, ev):
        global flow_list
        msg = ev.msg
        dp = msg.datapath
        data = msg.data
        if msg.reason == dp.ofproto.OFPET_HELLO_FAILED:
            reason = 'OFPET_HELLO_FAILED'
        elif msg.reason == dp.ofproto.OFPET_BAD_REQUEST:
            reason = 'OFPET_BAD_REQUEST'
        elif msg.reason == dp.ofproto.OFPET_BAD_ACTION:
            reason = 'OFPET_BAD_ACTION'
        elif msg.reason == dp.ofproto.OFPET_FLOW_MOD_FAILED:
            reason = 'OFPET_FLOW_MOD_FAILED'
        elif msg.reason == dp.ofproto.OFPET_PORT_MOD_FAILED:
            reason = 'OFPET_PORT_MOD_FAILED'
        else:
            reason = 'OFPET_QUEUE_OP_FAILED'
        flow_list.append({'type':'ERROR','timestamp': ev.timestamp, 'datapath_id': dp.id, 'data': data, 'reason': reason})
        #write_file({'type':'ERROR','timestamp': ev.timestamp, 'datapath_id': dp.id, 'data': data, 'reason': reason})


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
        #write_file(str('FlowStats: %s', flows))
    
    # it may send OFPPC_NO_PACKET_IN when table is full ?
    def _send_port_mod(self, dp, config, mask):
        p = self.get_port(dp)
        if not p:
            err = 'need attached port to switch.'
            self.results[self.current] = err
            self.start_next_test(dp)
            return

        self._verify = [p.port_no, config & mask]
        m = dp.ofproto_parser.OFPPortMod(dp, p.port_no, p.hw_addr,
                                         config, mask, 0)
        dp.send_msg(m)
        dp.send_barrier()

        # TODO: waiting to port UP|DOWN.
        time.sleep(1)
        m = dp.ofproto_parser.OFPFeaturesRequest(dp)
        print("Checkk! for table_full")
        print(f"Flow removed from datapath {dp.id}, message: {m}")
        #write_file(f"Flow removed from datapath {dp.id}, message: {m}")
        dp.send_msg(m)

    #for sending stat req, then listen it
    def send_flow_stats_request(self, datapath):
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
        
    @set_ev_cls(ofp_event.EventOFPAggregateStatsReply, MAIN_DISPATCHER)
    def aggregate_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.debug('AggregateStats: packet_count=%d byte_count=%d '
                        'flow_count=%d',
                        body.packet_count, body.byte_count,
                        body.flow_count)
        print(f"AggregateStats: packet_count={body.packet_count} byte_count={body.byte_count} flow_count={body.flow_count}'")
        #write_file(f"AggregateStats: packet_count={body.packet_count} byte_count={body.byte_count} flow_count={body.flow_count}'")
        
    """
        {
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
    }
    """

    #try to send post request from postman, listen and log it here:
    @set_ev_cls(ofp_event.EventOFPTableStatsReply, MAIN_DISPATCHER)
    def table_stats_reply_handler(self, ev):
        tables = []
        for stat in ev.msg.body:
            tables.append('table_id=%d active_count=%d lookup_count=%d '
                        ' matched_count=%d' %
                        (stat.table_id, stat.active_count,
                        stat.lookup_count, stat.matched_count))
        self.logger.debug('TableStats: %s', tables)
        print(f"AggregateStats: table_id={stat.table_id} active_count={stat.active_count} lookup_count={stat.lookup_count} matched_count={stat.matched_count}")
        #write_file(f"AggregateStats: table_id={stat.table_id} active_count={stat.active_count} lookup_count={stat.lookup_count} matched_count={stat.matched_count}")

    

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        ports = []
        for stat in ev.msg.body:
            ports.append('port_no=%d '
                        'rx_packets=%d tx_packets=%d '
                        'rx_bytes=%d tx_bytes=%d '
                        'rx_dropped=%d tx_dropped=%d '
                        'rx_errors=%d tx_errors=%d '
                        'rx_frame_err=%d rx_over_err=%d rx_crc_err=%d '
                        'collisions=%d duration_sec=%d duration_nsec=%d' %
                        (stat.port_no,
                        stat.rx_packets, stat.tx_packets,
                        stat.rx_bytes, stat.tx_bytes,
                        stat.rx_dropped, stat.tx_dropped,
                        stat.rx_errors, stat.tx_errors,
                        stat.rx_frame_err, stat.rx_over_err,
                        stat.rx_crc_err, stat.collisions,
                        stat.duration_sec, stat.duration_nsec))
        self.logger.debug('PortStats: %s', ports)
        #write_file(str('PortStats: %s', ports))

    @set_ev_cls(ofp_event.EventOFPAggregateStatsReply, MAIN_DISPATCHER)
    def aggregate_stats_reply_handler(self, ev):
        body = ev.msg.body

        self.logger.debug('AggregateStats: packet_count=%d byte_count=%d '
                        'flow_count=%d',
                        body.packet_count, body.byte_count,
                        body.flow_count)
        #write_file('AggregateStats: packet_count=%d byte_count=%d ''flow_count=%d',body.packet_count, body.byte_count,body.flow_count)


    