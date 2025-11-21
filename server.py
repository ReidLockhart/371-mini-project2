import socket
import time
from util import *
import threading
import random

#
# Set up whats needed for connection
BUFFER_SIZE = 24
CURRENT_BUFFER_SIZE = 0

#
# for concurrency
buffer_lock = threading.Lock()

expected_seq = 0
connected = False
client_addr = None
has_syn = False
has_fin = False
total_message = ""
buffer = []

def reset_connection():
    global expected_seq, connected, client_addr, has_syn, has_fin, total_message, BUFFER_SIZE, CURRENT_BUFFER_SIZE, buffer
    expected_seq = 0
    connected = False
    client_addr = None
    has_syn = False
    has_fin = False
    total_message = ""
    BUFFER_SIZE = 24
    CURRENT_BUFFER_SIZE = 0
    buffer = []

def process_buffer():
    global CURRENT_BUFFER_SIZE, BUFFER_SIZE, total_message, buffer

    while True:
        time.sleep(random.uniform(0.001, 0.01))
        with buffer_lock:
            if CURRENT_BUFFER_SIZE > 0:
                seq, msg = buffer.pop(0)
                CURRENT_BUFFER_SIZE -= 1
                rwnd = BUFFER_SIZE - CURRENT_BUFFER_SIZE
                print(f"Received: seq = {seq}; data = {msg}")
            else:
                time.sleep(0.005)
                continue

def start_server():
    global expected_seq, connected, client_addr, has_syn, has_fin, total_message, BUFFER_SIZE, CURRENT_BUFFER_SIZE, buffer
    #
    # set up UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    sock.settimeout(1.0)
    print(f"Server listening on port {SERVER_PORT}")

    #
    # Start processing queue
    threading.Thread(target=process_buffer, daemon=True).start()
        
    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)

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
                    with buffer_lock:
                        return_ack = create_packet(0, seq + 1, ACK_FLAG | SYN_FLAG, (BUFFER_SIZE - CURRENT_BUFFER_SIZE), b"")
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
                with buffer_lock:
                    fin_ack = create_packet(0, seq + 1, ACK_FLAG, (BUFFER_SIZE - CURRENT_BUFFER_SIZE), b"")
                    fin_msg = create_packet(0, seq + 1, FIN_FLAG, (BUFFER_SIZE - CURRENT_BUFFER_SIZE), b"")
                sock.sendto(fin_ack, addr)
                sock.sendto(fin_msg, addr)
                continue

            if has_fin and (flags & ACK_FLAG):
                print(f"Closing (2/2)\nfinal message is: \"{total_message}\"")
                reset_connection()
                continue

            #
            # Indicates this is a data message
            if (flags & DATA_FLAG):
                with buffer_lock:
                    if CURRENT_BUFFER_SIZE < BUFFER_SIZE:
                        if seq == expected_seq:
                            expected_seq += 1
                            CURRENT_BUFFER_SIZE += 1
                            #
                            # process the packet while still getting more
                            msg = payload.decode('utf-8')
                            total_message += msg
                            buffer.append((seq, msg))
                        else:
                            print(f"WARNING: Out of order. Expected: {expected_seq}, Received: {seq})")

                        ack_pkt = create_packet(0, expected_seq - 1, ACK_FLAG, (BUFFER_SIZE - CURRENT_BUFFER_SIZE), b"")
                        sock.sendto(ack_pkt, addr)
                    else:
                        print(f"WARNING: Buffer full. Discarding packet with seq = {seq}")

    except KeyboardInterrupt:
        print("\n\nShutting down...")
        sock.close()

if __name__ == "__main__":
    start_server()