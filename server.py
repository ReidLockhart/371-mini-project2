import socket
import time
from util import *
import threading

#
# Set up whats needed for connection
RECV_BUFFER = BUFFER_SIZE

expected_seq = 0
rwnd = 10
connected = False
client_addr = None
has_syn = False
has_fin = False
total_message = ""

def reset_connection():
    global expected_seq, rwnd, connected, client_addr, has_syn, has_fin, total_message
    expected_seq = 0
    rwnd = 10
    connected = False
    client_addr = None
    has_syn = False
    has_fin = False
    total_message = ""

def start_server():
    global expected_seq, rwnd, connected, client_addr, has_syn, has_fin, total_message
    #
    # set up UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    sock.settimeout(1.0)
    print(f"Server listening on port {SERVER_PORT}")
        
    try:
        while True:
            try:
                data, addr = sock.recvfrom(RECV_BUFFER)

            except socket.timeout:
                continue
            #
            # Does it match the current connection or the potential connection?
            if client_addr is not None and addr != client_addr:
                continue
            #
            # Parse the packet from the UDP payload
            packet = parse_packet(data)
            if not packet:
                print("ERROR: Corrupted packet. Ignored.")
                continue

            seq, ack, flags, recv_rwnd, payload = packet

            if not connected:

                if (flags & SYN_FLAG): # first part in 3-way handshake
                    print(f"SYN received from {addr}. Connected (1/2)")
                    return_ack = create_packet(0, seq + 1, ACK_FLAG | SYN_FLAG, rwnd, b"")
                    sock.sendto(return_ack, addr)
                    has_syn = True
                    client_addr = addr
                    continue

                if has_syn and (flags & ACK_FLAG): # finished opening connection
                    print(f"ACK received from {addr}. Connected (2/2)")
                    #
                    # Set up the connection
                    connected = True
                    expected_seq = 0
                    has_syn = False
                    continue

                #
                # If we get here just ignore the packet
                continue
        
            if not has_fin and (flags & FIN_FLAG):
                has_fin = True
                print("FIN received.  Closing (1/2)")
                fin_ack = create_packet(0, seq + 1, ACK_FLAG, rwnd, b"")
                sock.sendto(fin_ack, addr)

                fin_msg = create_packet(0, seq + 1, FIN_FLAG, rwnd, b"")
                sock.sendto(fin_msg, addr)
                continue

            if has_fin and (flags & ACK_FLAG):
                print(f"Closing (2/2)\nfinal message is: \"{total_message}\"")
                reset_connection()
                continue

            #
            # Indicates this is a data message
            if (flags & DATA_FLAG):
                if seq == expected_seq:
                    msg = payload.decode(errors='ignore')
                    total_message += msg
                    print(f"Received (seq, data): {seq}, data={msg}")
                    expected_seq += 1
                else:
                    print(f"WARNING: Out of order. Expected: {expected_seq}, Received: {seq})")

                ack_pkt = create_packet(0, expected_seq - 1, ACK_FLAG, rwnd, b"")
                sock.sendto(ack_pkt, addr)

    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sock.close()

if __name__ == "__main__":
    start_server()