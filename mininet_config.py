from mininet.net import Mininet
from mininet.topo import LinearTopo
from mininet.topolib import TreeTopo
from mininet.node import Controller, RemoteController, Node
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from parameters import TABLE_CAPACITY
import sys
import benign_traffic
import attack_sim

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
            self.master_node.cmdPrint(f'ovs-vsctl -- --id=@{switch} create Flow_Table flow_limit={TABLE_CAPACITY} overflow_policy=refuse -- set Bridge {switch} flow_tables=0=@{switch}')
    def pingAll(self):
        self.net.pingAll()
    def stop(self):
        self.net.stop()
        

if __name__ == '__main__':
    arguments = sys.argv
    topology = arguments[1] if len(arguments) > 1 else 'linear'
    number_of_switch = int(arguments[2]) if len(arguments) > 2 else 2

    number_of_host_per_switch = int(arguments[3]) if len(arguments) > 3 else 1
    topo = MininetTopo(topology, number_of_switch, number_of_host_per_switch)
    try:
        
        setLogLevel( 'debug' )
        print('Topology created')
        topo.start()
        topo.config_switch() 
        a = topo.net.hosts
        host = a[0]
        switch = a[1]
        # h1 = topo.net.get('h1')
        # h2 = topo.net.get('h2')
        # h2.cmd('python3 -m http.server 80 &')
        malicious = attack_sim.malicious_host('h1s1',host,10)
        malicious.attack_controller_ip(5, 60 ,number_of_host_per_switch*number_of_switch, 4)
        # benign_traffic.traffic(topo.net, number_of_host_per_switch*number_of_switch )
        CLI( topo.net )
        print('CLI opened')
        topo.stop()
    except Exception as e:
        print('ERROR:',e)
        
        topo.stop()
        
