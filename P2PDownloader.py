from socket import *
import sys

class UDP_socket:
   def __init__(self, file_name, serverName, serverPort) -> None:
      self.file_name = file_name
      self.serverName = serverName
      self.serverPort = serverPort
      self.socket = None
      
   def socket_init(self):
      self.socket = socket(AF_INET, SOCK_DGRAM) 

   def send(self, get_command):
      self.socket.sendto(get_command.encode(), (self.serverName, self.serverPort))
   
   def recv(self):
      return self.socket.recvfrom(2048)

   def get_ip(self):
      return gethostbyname(self.serverName)

   def close(self):
      self.socket.close()

   
serverName = str(sys.argv[2])
serverPort = int(sys.argv[3])
file_name = str(sys.argv[1])
get_command = "GET " + file_name + ".torrent" + "\n"

udp_socket = UDP_socket(file_name, serverName, serverPort)
udp_socket.socket_init()
udp_socket.send(get_command)
test = udp_socket.recv()
udp_socket.close()

# clientSocket = socket(AF_INET, SOCK_DGRAM)
# clientSocket.sendto(get_command.encode(), (serverName, serverPort))
# test = clientSocket.recvfrom(2048)
# print(type(test))
# print(test)
