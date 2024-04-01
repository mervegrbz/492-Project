from mininet.net import Mininet
from mininet.topo import LinearTopo
from mininet.node import Controller, RemoteController

Linear = LinearTopo()
net = Mininet(topo=Linear, controller=RemoteController)
class MininetTopo():
    def __init__(self):
        self.net = Mininet(topo=Linear, controller=RemoteController)
    def start(self):
        self.net.start()
    def pingAll(self):
        self.net.pingAll()
    def stop(self):
        self.net.stop()
