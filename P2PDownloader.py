from gc import collect
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
      self.socket.settimeout(0.5)
      try:
         data = self.socket.recvfrom(200)
         if data != None:
            return data
         else:
            self.send()
            return self.recv()
      except timeout:
         self.send()
         return self.recv()

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
      self.socket.settimeout(2)
      try:
         self.socket.connect((self.serverName, self.serverPort))
         self.socket.send(get_command.encode())
      except timeout:
         return self.get_block(block_number)

   #TODO PRIORITY: Handle TCP Server disconnection while downloading
   def recv(self, block_number=None):
      data = b''

      #UNDESTANDING: Collect header file until body of bytes starts
      while b'\n\n' not in data:
         self.socket.settimeout(2)
         try:
            data += self.socket.recv(512)
         except timeout:
            self.socket.close()
            self.socket = self.socket_init()
            self.get_block(block_number)
            return self.recv()
      
      data_tok = data.split(b"\n")
      data_length = int(data_tok[2][18:])
      data_offset = int(data_tok[1][26:])
      data = data.split(b"\n\n")
      block_data = data[1]
      print(data[0])
      data_length -= len(block_data)

      while data_length > 0:
         self.socket.settimeout(2)
         try:
            data = self.socket.recv(512)
            block_data += data
            data_length -= len(data)
         except timeout:
            self.socket.close()
            self.socket = self.socket_init()
            self.get_block(block_number)
            return self.recv()
      

      return (block_data, data_offset)
   
   def close(self):
      self.socket.close()


def tcp_thread_requests(cblocks_lock, mblocks_lock, ap_lock, file_name, peer, num_blocks):
   global collected_blocks, missing_blocks, active_peers, peers_set

   # udp_socket = UDP_socket()
   # udp_socket.send()
   # msg = udp_socket.recv()
   # udp_socket.close()
   
   # if msg != None:
   #    num_blocks, file_size, temp_peers = udp_socket.get_metadata(msg[0])
   #    ap_lock.acquire()
   #    for peer in temp_peers:
   #       if peer not in active_peers:
   #          peers_set.add(peer)
   #    ap_lock.release()
   
   

   while len(collected_blocks) != num_blocks and len(missing_blocks) != 0:
      mblocks_lock.acquire()
      if missing_blocks:
         curr_block = missing_blocks.pop()
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
      # print("***COLLECTED_BLOCKS***", len(collected_blocks), threading.get_ident())
      blocks = len(collected_blocks)
      cblocks_lock.release()

   # print("hello world")
   tcp_socket.close()


def block_to_image(collected_blocks: dict, image_name: str):
   image_file = open(image_name, 'wb')
   image_start = timer()
   for block in sorted(collected_blocks):
      image_file.write(collected_blocks[block])
   image_file.close()
   image_end = timer()
   print("image writing time: ", image_end-image_start)


def main():
   start = timer()

   global collected_blocks, missing_blocks, active_peers, peers_set
   active_peers = set()
   ap_lock = threading.Lock()
   collected_blocks = dict()
   cblocks_lock = threading.Lock()
   mblocks_lock = threading.Lock()
   peers_set = set()

   # if msg != None:
   #    num_blocks, file_size, temp_set = udp_socket.get_metadata(msg[0])
   #    missing_blocks = [*range(num_blocks)]
   #    for elem in temp_set:
   #       peers_set.add(elem)
   udp_socket = UDP_socket()
   
   sock_start = timer()
   for _ in range(3):
      udp_socket.send()

      recv_start = timer()
      msg = udp_socket.recv()
      recv_end = timer()
      print("RECV TIMER: ", recv_end-recv_start )

      num_blocks, file_size, temp_set = udp_socket.get_metadata(msg[0])
      missing_blocks = [*range(num_blocks)]
      for elem in temp_set:
         peers_set.add(elem)
   sock_end = timer()
   print("SOCKETS TIMER: ", sock_end-sock_start)
   udp_socket.close()

   for _ in range(len(peers_set) - 5):
      peers_set.pop()

   thread_arr = []
   while peers_set and len(collected_blocks) != num_blocks:
      popped_peer = peers_set.pop()
      if popped_peer not in active_peers:
         active_peers.add(popped_peer)
         curr_thread = threading.Thread(target=tcp_thread_requests, args=(cblocks_lock, mblocks_lock, ap_lock, udp_socket.file_name, popped_peer, num_blocks))
         thread_arr.append(curr_thread)
         curr_thread.start()
   # print("out of while")
   for thread in thread_arr:
      thread.join()
   
   # print("bananas")
   
   block_to_image(collected_blocks, udp_socket.file_name)
   end = timer()
   print("download time: ", end-start)

   
main()
sys.exit(0)
