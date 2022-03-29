from socket import *
import sys
import threading
from timeit import default_timer as timer

class UDP_socket:
   def __init__(self):
      self.file_name = str(sys.argv[1])
      self.serverName = str(sys.argv[2])
      self.serverPort = int(sys.argv[3])
      self.get_command = "GET " + self.file_name + ".torrent" + "\n"
      self.socket = self.socket_init()
      
   def socket_init(self):
      return socket(AF_INET, SOCK_DGRAM) 

   def send(self):
      self.socket.sendto(self.get_command.encode(), (self.serverName, self.serverPort))
   
   def recv(self):
      self.socket.settimeout(3)
      try:
         data = self.socket.recvfrom(500)
         if data != None:
            print(data)
            return data
         else:
            self.send()
            self.recv()
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
      self.socket = self.socket_init()

   def socket_init(self):
      return socket(AF_INET, SOCK_STREAM)
   
   def get_block(self, block_number=None):
      get_command = str()
      if block_number != None:
         get_command = "GET " + self.file_name + ":" + str(block_number) + "\n"
      else:
         get_command = "GET " + self.file_name + ":*" + "\n"

      self.socket.connect((self.serverName, self.serverPort))
      self.socket.send(get_command.encode())

   #TODO PRIORITY: Handle TCP Server disconnection while downloading
   def recv(self, block_number=None):
      data = b''

      #UNDESTANDING: Collect header file until body of bytes starts
      while b'\n\n' not in data:
         self.socket.settimeout(5)
         try:
            data += self.socket.recv(512)
         except timeout:
            self.socket.close()
            self.socket = self.socket_init()
            self.get_block(block_number)
            self.recv()
      
      data_tok = data.split(b"\n")
      data_length = int(data_tok[2][18:])
      data_offset = int(data_tok[1][26:])
      data = data.split(b"\n\n")
      block_data = data[1]
      print(data[0])
      data_length -= len(block_data)

      while data_length > 0:
         self.socket.settimeout(5)
         try:
            data = self.socket.recv(512)
            block_data += data
            data_length -= len(data)
         except timeout:
            self.socket.close()
            self.socket = self.socket_init()
            self.get_block(block_number)
            self.recv()
      

      return (block_data, data_offset)
   
   def close(self):
      self.socket.close()


def tcp_thread_requests(cblocks_lock, mblocks_lock, ap_lock, file_name, peer, num_blocks):
   global collected_blocks, missing_blocks, active_peers, peers_set
   
   udp_socket = UDP_socket()
   udp_socket.send()
   msg = udp_socket.recv()
   udp_socket.close()
   
   if msg != None:
      num_blocks, file_size, temp_peers = udp_socket.get_metadata(msg[0])
      print("In threads: {}", temp_peers)
      ap_lock.acquire()
      for peer in temp_peers:
         peers_set.add(peer)
      ap_lock.release()
      
   while len(collected_blocks) != num_blocks:
      mblocks_lock.acquire()
      if missing_blocks:
         curr_block = missing_blocks.pop()
         print(curr_block)
      else:
         break
      mblocks_lock.release()

      server_address = peer[0]
      server_port = peer[1]
      tcp_socket = TCP_socket(server_address, server_port)

      tcp_socket.get_block(curr_block)
      block_data, data_offset = tcp_socket.recv(curr_block) #TODO: Needs to download disconnection and request disconnectoin

      cblocks_lock.acquire()
      collected_blocks[curr_block] = block_data
      cblocks_lock.release()

   tcp_socket.close()


def block_to_image(collected_blocks: dict, image_name: str):
   image_file = open(image_name, 'wb')
   for block in sorted(collected_blocks):
      image_file.write(collected_blocks[block])
   image_file.close()


def main():
   start = timer()

   global collected_blocks, missing_blocks, active_peers, peers_set
   active_peers = set()
   ap_lock = threading.Lock()
   collected_blocks = dict()
   cblocks_lock = threading.Lock()
   mblocks_lock = threading.Lock()
   peers_set = set()

   #TODO: PRIORITY Set UDP Timeout
   udp_socket = UDP_socket()
   udp_socket.send()
   msg = udp_socket.recv()
   udp_socket.close()

   #TODO: Create get_tracker_data for UDP class
   if msg != None:
      num_blocks, file_size, temp_set = udp_socket.get_metadata(msg[0])
      missing_blocks = [*range(num_blocks)]
      for elem in temp_set:
         peers_set.add(elem)
   
   print(peers_set)
   thread_arr = []
   while peers_set:
      popped_peer = peers_set.pop()
      if popped_peer not in active_peers:
         active_peers.add(popped_peer)
         curr_thread = threading.Thread(target=tcp_thread_requests, args=(cblocks_lock, mblocks_lock, ap_lock, udp_socket.file_name, popped_peer, num_blocks))
         thread_arr.append(curr_thread)
         curr_thread.start()

   for thread in thread_arr:
      thread.join()
      
   block_to_image(collected_blocks, udp_socket.file_name)
   end = timer()
   print(end-start)

   

main()
sys.exit(0)
