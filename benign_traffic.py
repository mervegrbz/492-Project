from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.node import OVSKernelSwitch, RemoteController
from time import sleep

from datetime import datetime
from random import randrange, choice


def ip_generator():

    ip = ".".join(["10","0","0",str(randrange(1,2))])
    return ip
        
def traffic(net: Mininet):
    
    h1 = net.get('h1')
    h2 = net.get('h2')

   
    
    hosts = [h1, h2]    
    print("--------------------------------------------------------------------------------")    
    print("Generating traffic ...")    
    h1.cmd('python3 -m http.server 80 &')
    h1.cmd('iperf -s -p 5050 &')
    h1.cmd('iperf -s -u -p 5051 &')
    sleep(2)
    
    
    for i in range(6):
        
        print("--------------------------------------------------------------------------------")    
        print("Iteration n {} ...".format(i+1))
        print("--------------------------------------------------------------------------------") 
        
        for j in range(2):
            src = choice(hosts)
            dst = ip_generator()
            
            if j <9:
                print("generating ICMP traffic between %s and h%s and TCP/UDP traffic between %s and h1" % (src,((dst.split('.'))[3]),src))
                src.cmd("ping {} -c 100 &".format(dst))
                src.cmd("iperf -p 5050 -c 10.0.0.1")
                src.cmd("iperf -p 5051 -u -c 10.0.0.1")
            else:
                print("generating ICMP traffic between %s and h%s and TCP/UDP traffic between %s and h1" % (src,((dst.split('.'))[3]),src))
                src.cmd("ping {} -c 100".format(dst))
                src.cmd("iperf -p 5050 -c 10.0.0.1")
                src.cmd("iperf -p 5051 -u -c 10.0.0.1")
            
            # print("%s Downloading index.html from h1" % src)
            # src.cmd("wget http://10.0.0.1/index.html")
            # print("%s Downloading test.zip from h1" % src)
            # src.cmd("wget http://10.0.0.1/test.zip")
        
        # h1.cmd("rm -f *.* /home/mininet/Downloads")
        
    print("--------------------------------------------------------------------------------")  
    
    # CLI(net)
   

if __name__ == '__main__':
    
    start = datetime.now()
    
    setLogLevel( 'info' )
    traffic(Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink))
    
    end = datetime.now()
    
    print(end-start)