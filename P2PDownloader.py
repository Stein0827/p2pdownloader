from socket import *
import sys
import threading

class UDP_socket:
   def __init__(self):
      self.file_name = str(sys.argv[1])
      self.serverName = str(sys.argv[2])
      self.serverPort = int(sys.argv[3])
      self.get_command = "GET " + self.file_name + ".torrent" + "\n"
      self.socket = None
      
   def socket_init(self):
      self.socket = socket(AF_INET, SOCK_DGRAM) 

   def send(self):
      self.socket.sendto(self.get_command.encode(), (self.serverName, self.serverPort))
   
   def recv(self):
      return self.socket.recvfrom(500)

   def get_ip(self):
      return gethostbyname(self.serverName)

   def get_metadata(self, msg):
      meta_data = str.split(msg.decode(), "\n")
      num_blocks = int(meta_data[0][12:])
      file_size = int(meta_data[1][11:])
      peers = {(meta_data[2][5:], int(meta_data[3][7:])), (meta_data[4][5:], int(meta_data[5][7:]))}
      return (num_blocks, file_size, peers)

   def close(self):
      self.socket.close()


class TCP_socket:
   def __init__(self, file_name, serverName, serverPort):
      self.file_name = file_name
      self.serverName = serverName
      self.serverPort = serverPort

   def socket_init(self):
      self.socket = socket(AF_INET, SOCK_STREAM)
   
   def get_block(self, is_num):
      get_command = str()
      if is_num:
         get_command = "GET " + self.file_name + ":" + str(self.block_number) + "\n"
      else:
         get_command = "GET " + self.file_name + ":*" + "\n"
      
      self.socket.connect((self.serverName, self.serverPort))
      self.socket.send(get_command.encode())

   def recv(self):
      data = b''

      while b'\n\n' not in data:
         data += self.socket.recv(2046)
      
      data_tok = data.split(b"\n")
      data_length = int(data_tok[2][18:])
      data_offset = int(data_tok[1][27:])
      data = data.split(b"\n\n")
      block_data = data[1]
      data_length -= len(block_data)

      while data_length > 0:
         data = self.socket.recv(2046)
         block_data += data
         data_length -= len(data)

      return (block_data, data_offset)
   
   def close(self):
      self.socket.close()



def main():
   #TODO: PRIORITY Set UDP Timeout
   udp_socket = UDP_socket()
   udp_socket.socket_init()
   udp_socket.send()

   msg, serverAddress = udp_socket.recv()

   num_blocks, file_size, peers = udp_socket.get_metadata(msg)

   udp_socket.close()
   

main()
sys.exit(0)

