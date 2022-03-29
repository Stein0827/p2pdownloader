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
      self.socket.settimeout(0.5)
      try:
         data = self.socket.recvfrom(500)
         return data
      except timeout:
         self.send()
         self.recv()


   def get_ip(self):
      return gethostbyname(self.serverName)

   def get_metadata(self, msg):
      meta_data = str.split(msg.decode(), "\n")
      num_blocks = int(meta_data[0][12:])
      file_size = int(meta_data[1][11:])
      peers_set = {(meta_data[2][5:], int(meta_data[3][7:])), (meta_data[4][5:], int(meta_data[5][7:]))}
      return (num_blocks, file_size, peers_set)

   def close(self):
      self.socket.close()


class TCP_socket:
   def __init__(self, serverName, serverPort):
      self.file_name = str(sys.argv[1])
      self.serverName = serverName
      self.serverPort = serverPort

   def socket_init(self):
      self.socket = socket(AF_INET, SOCK_STREAM)
   
   def get_block(self, block_number=None):
      get_command = str()
      if block_number != None:
         get_command = "GET " + self.file_name + ":" + str(block_number) + "\n"
      else:
         get_command = "GET " + self.file_name + ":*" + "\n"

      self.socket.connect((self.serverName, self.serverPort))
      self.socket.send(get_command.encode())

   #TODO PRIORITY: Handle TCP Server disconnection while downloading
   def recv(self):
      data = b''
      print("in recv")

      #UNDESTANDING: Collect header file until body of bytes starts
      while b'\n\n' not in data:
         self.socket.settimeout(1)
         try:
            data += self.socket.recv(2046)
         except timeout:
            print("timed out")
            self.recv()
      
      data_tok = data.split(b"\n")
      print(data_tok)
      data_length = int(data_tok[2][18:])
      data_offset = int(data_tok[1][26:])
      data = data.split(b"\n\n")
      block_data = data[1]
      data_length -= len(block_data)
      # print("***TCP REQUEST*** " + str(data[0]))

      while data_length > 0:
         data = self.socket.recv(2046)
         block_data += data
         data_length -= len(data)
      
      print(len(block_data))
      print(data_length)

      return (block_data, data_offset)
   
   def close(self):
      self.socket.close()

def tcp_thread_requests(cblocks_lock, mblocks_lock, ap_lock, file_name, peer, num_blocks):
   global collected_blocks, missing_blocks, active_peers

   while len(collected_blocks) != num_blocks:
      mblocks_lock.acquire()
      if missing_blocks:
         curr_block = missing_blocks.pop()
      mblocks_lock.release()


      server_address = peer[0]
      server_port = peer[1]
      tcp_socket = TCP_socket(server_address, server_port)
      tcp_socket.socket_init()

      print("before get block")
      tcp_socket.get_block(curr_block)
      print("after get block")
      print("before recv")
      block_data, data_offset = tcp_socket.recv() #TODO: Needs to download disconnection and request disconnectoin
      print("after recv")

      cblocks_lock.acquire()
      collected_blocks[num_blocks] = block_data
      cblocks_lock.release()


def main():
   #TODO: PRIORITY Set UDP Timeout
   udp_socket = UDP_socket()
   udp_socket.socket_init()
   udp_socket.send()
   msg, serverAddress = udp_socket.recv()
   print(msg, serverAddress)

   #TODO: Create get_tracker_data for UDP class
   num_blocks, file_size, peers_set = udp_socket.get_metadata(msg)
   print(num_blocks, file_size, peers_set)

   global collected_blocks, missing_blocks, active_peers
   active_peers = set()
   ap_lock = threading.Lock()
   collected_blocks = dict()
   cblocks_lock = threading.Lock()
   missing_blocks = [*range(num_blocks)]
   mblocks_lock = threading.Lock()

   while len(collected_blocks) != num_blocks:
      # udp_socket.send()
      # msg, serverAddress = udp_socket.recv()
      # print(msg, serverAddress)
      # num_blocks, file_size, peers_set = udp_socket.get_metadata(msg)
      thread_arr = []

      for peer in peers_set:
         if peer not in active_peers:
            active_peers.add(peer)
            curr_thread = threading.Thread(target=tcp_thread_requests, args=(cblocks_lock, mblocks_lock, ap_lock, udp_socket.file_name, peer, num_blocks))
            thread_arr.append(curr_thread)
            curr_thread.start()

      for thread in thread_arr:
         thread.join()

   udp_socket.close()
   

main()
sys.exit(0)
