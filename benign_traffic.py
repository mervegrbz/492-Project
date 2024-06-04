from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.node import OVSKernelSwitch, RemoteController
from time import sleep

from datetime import datetime
from random import randrange, choice


def ip_generator(number_of_hosts=2):

    ip = ".".join(["10","0","0",str(randrange(1,number_of_hosts))])
    return ip
        
def traffic(net: Mininet, number_of_hosts=2):
    hosts = net.hosts
            
    print("--------------------------------------------------------------------------------")    
    print("Generating traffic ...")    
    sleep(2)
    
    host_http = choice(hosts)
    host_http.cmd('python3 -m http.server 80&')
    for i in range(10): # how many times you would simulate the traffic
        ## randomly select two server hosts
        host_udp = choice(hosts)
        host_udp.cmd('iperf -s -u -p 5050 -t 20 &')
        host_tcp = choice(hosts)
        host_tcp.cmd('iperf -s -p 5050 -t 20 &')
        sleep(2)
        
        print("--------------------------------------------------------------------------------")    
        print("--------------------------------------------------------------------------------") 
        src = choice(hosts)
        dst = ip_generator(number_of_hosts)
        while(src == dst):
            dst = ip_generator(number_of_hosts)
        
        print(f"generating ICMP traffic between {src} and h%s and TCP/UDP traffic between  and h1" )
        src.cmd(f"ping -c 2 {dst}")
        sleep(randrange(1,5))
        src.cmd(f"iperf -p 5050 -c 1 {host_tcp.IP()}")
        sleep(randrange(1,5))
        src.cmd(f"iperf -p 5051 -u -c 1 {host_udp.IP()}")
    
        print("%s Downloading index.html from h1" % src)
        src.cmd("wget http://10.0.0.1/index.html")
        sleep(2)
        # h1.cmd("rm -f *.* /home/mininet/Downloads")

        
    print("--------------------------------------------------------------------------------")  
    
    # CLI(net)
   

if __name__ == '__main__':
    
    start = datetime.now()
    
    setLogLevel( 'info' )
    traffic(Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink))
    
    end = datetime.now()
    
    print(end-start)