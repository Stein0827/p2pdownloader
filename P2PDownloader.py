from socket import *
import sys

serverName = str(sys.argv[2])
serverPort = int(sys.argv[3])
torrent_name = str(sys.argv[1])
get_command = "GET " + torrent_name + "\n"


clientSocket = socket(AF_INET, SOCK_DGRAM)
clientSocket.sendto(get_command.encode(), (serverName, serverPort))
test = clientSocket.recvfrom(2048)
print(type(test))
print(test)
