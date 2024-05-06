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
    hosts = []
    for i in range(1, number_of_hosts+1):
        hosts.append(net.get('h%s' % i))

    
    print("--------------------------------------------------------------------------------")    
    print("Generating traffic ...")    
    hosts[0].cmd('python3 -m http.server 80 &')
    hosts[0].cmd('iperf -s -p 5050 &')
    hosts[0].cmd('iperf -s -u -p 5051 &')
    sleep(2)
    
    
    for i in range(2): # how many times you would simulate the traffic
        
        print("--------------------------------------------------------------------------------")    
        print("Iteration n {} ...".format(i+1))
        print("--------------------------------------------------------------------------------") 
        
        for j in range(number_of_hosts):
            src = choice(hosts)
            dst = ip_generator(number_of_hosts)

            print(f"generating ICMP traffic between {src} and h%s and TCP/UDP traffic between %s and h1" % (src,((dst.split('.'))[3]),src))
            src.cmd(f"ping {dst} -c 10 &")
            src.cmd("iperf -p 5050 -c 10.0.0.1")
            src.cmd("iperf -p 5051 -u -c 10.0.0.1")
        
            print("%s Downloading index.html from h1" % src)
            src.cmd("wget http://10.0.0.1/index.html")
        
        # h1.cmd("rm -f *.* /home/mininet/Downloads")
        
    print("--------------------------------------------------------------------------------")  
    
    # CLI(net)
   

if __name__ == '__main__':
    
    start = datetime.now()
    
    setLogLevel( 'info' )
    traffic(Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink))
    
    end = datetime.now()
    
    print(end-start)