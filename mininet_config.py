from mininet.net import Mininet
from mininet.topo import LinearTopo
from mininet.topolib import TreeTopo
from mininet.node import Controller, RemoteController, Node
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import sys


class MininetTopo():
    def __init__(self, topology = 'linear', number_of_switch = 2 , number_of_host_per_switch = 1):
        if topology == 'linear':
            Linear = LinearTopo(number_of_switch, number_of_host_per_switch)
            self.net = Mininet(topo=Linear, controller=RemoteController)
        elif topology == 'tree':
            TreeTopo = TreeTopo(number_of_switch, number_of_host_per_switch)
            self.net = Mininet(topo=TreeTopo, controller=RemoteController)
        else:
            print('Invalid topology')
            sys.exit(1)
        self.master_node = Node('master')
        
    def start(self):
        self.net.start()
        
    def config_switch(self):
        for switch in self.net.switches:
            self.master_node.cmdPrint('ovs-vsctl set bridge %s protocols=OpenFlow13' %switch)
            # limit the flow table 
            print(switch)
            self.master_node.cmdPrint(f'ovs-vsctl -- --id=@{switch} create Flow_Table flow_limit=10 overflow_policy=refuse -- set Bridge {switch} flow_tables=0=@{switch}')
    def pingAll(self):
        self.net.pingAll()
    def stop(self):
        self.net.stop()
        

if __name__ == '__main__':
    arguments = sys.argv
    topology = 'linear'
    number_of_switch = 2
    number_of_host_per_switch = 1
    topo = None
    # runs on default configuration 
    if len(arguments) == 1:
        topo = MininetTopo()
    elif len(arguments) == 2:
        topology = arguments[1]
        if topology == 'linear':
            topo = MininetTopo()
        elif topology == 'tree':
            topo = MininetTopo()
        else:
            print('Invalid topology')
            sys.exit(1)
    elif len(arguments) > 3:
        topology = arguments[1]
        number_of_switch = int(arguments[2])
        number_of_host_per_switch = int(arguments[3])
        if topology == 'linear':
            topo = MininetTopo()
        elif topology == 'tree':
            topo = MininetTopo()
        else:
            print('Invalid topology')
            sys.exit(1)
            
    
    try:
        
        setLogLevel( 'debug' )
        print('Topology created')
        topo.start()
        topo.config_switch()
        CLI( topo.net )
        print('CLI opened')
        topo.stop()
    except Exception as e:
        print('ERROR:',e)
        
        topo.stop()
        