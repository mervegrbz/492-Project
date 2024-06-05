from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.node import OVSKernelSwitch, RemoteController
from time import sleep
from random import randint
from datetime import datetime
from random import randrange, choice


def ip_generator(number_of_hosts=2):

    ip = ".".join(["10","0","0",str(randrange(1,number_of_hosts))])
    return ip
        
def traffic(net: Mininet, number_of_hosts=2):
    hosts = net.hosts
            
    print("--------------------------------------------------------------------------------")    
    print("Generating traffic ...")    
    sleep(3)
    
    host_http = choice(hosts)
    host_http.cmd('python3 -m http.server 80 &')
    host_udp = choice(hosts)
    host_udp.cmd('iperf3 -s -p 5051 &')
    host_tcp = choice(hosts)
    host_tcp.cmd('iperf3 -s -p 5050 &')
    
    for i in range(30): # how many times you would simulate the traffic
        ## randomly select two server hosts
        sleep(randint(3,10))
        
        print("--------------------------------------------------------------------------------")    
        print("--------------------------------------------------------------------------------") 
        src = choice(hosts)
        dst = ip_generator(number_of_hosts)
        while(src == dst):
            dst = ip_generator(number_of_hosts)
        source = randint(0,9000)
        des = randint(0,9000)
        random_val = randint(0,4)
        print(f"generating ICMP traffic between {src} and h%s and TCP/UDP traffic between  and h1" )
        if(random_val ==0):
            src.cmd(f"hping3 -c 2 -p {source} -s {des} {dst}")
            print(source, des, dst)
        if(random_val == 1):
            sleep(randrange(1,5))
            src.cmd(f"iperf3 -c {host_tcp.IP()} -p 5050 --cport {source} -t 3  -l 30 &")
        if(random_val == 2):
            sleep(randrange(1,5))
            src.cmd(f"iperf3 -u -c {host_udp.IP()} -p 5051 --cport {source} -t 3 -l 30 &")
        else:
            print("%s Downloading index.html from h1" % src)
            src.cmd(f"wget http://{host_http.IP()}/index.html")
            sleep(2)
    
    print("--------------------------------------------------------------------------------")  
    
    # CLI(net)
   

if __name__ == '__main__':
    
    start = datetime.now()
    
    setLogLevel( 'info' )
    traffic(Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink))
    
    end = datetime.now()
    
    print(end-start)