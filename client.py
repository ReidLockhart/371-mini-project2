import socket
import time
from util import *

SERVER_ADDR = ("127.0.0.1", 9000)
CLIENT_RWND = 20
TIMEOUT = 1.0
RECV_BUFFER = BUFFER_SIZE


def start_client():

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5.0)

    connected = False
    has_fin = False
    expected_ack = 0

    send_base = 0
    next_seq = 0
    window_size = 4

    print("Client started.")

    #
    # send the Syn packet
    syn_packet = create_packet(0, 0, SYN_FLAG, CLIENT_RWND, b"")
    sock.sendto(syn_packet, SERVER_ADDR)
    print("Sent SYN")

    while not connected:
        try:
            data, addr = sock.recvfrom(RECV_BUFFER)
        except socket.timeout:
            print("Timed out while waiting for SYN-ACK. resending SYN")
            sock.sendto(syn_packet, SERVER_ADDR)
            continue

        packet = parse_packet(data)
        if not packet:
            continue

        seq, ack, flags, server_rwnd, payload = packet

        #
        # Has the server ACKed the first SYN?
        if flags & SYN_FLAG and flags & ACK_FLAG:
            print("Received SYN-ACK. Connection is open.")

            # Step 3: send final ACK
            final_connection_ack = create_packet(0, seq + 1, ACK_FLAG, CLIENT_RWND, b"")
            sock.sendto(final_connection_ack, SERVER_ADDR)
            print("Sent fianl connection ACK")

            connected = True
            break

    #
    #   --------------------
    # Start sending data
    #   --------------------
    #

    messages = [b"hello", b"World", b"!", b"This", b"is", b"a test."]

    while send_base < len(messages):
        #
        # Send current DATA packet
        while next_seq < send_base + window_size and next_seq < len(messages):
            pkt = create_packet(next_seq, 0, DATA_FLAG, CLIENT_RWND, messages[next_seq])
            sock.sendto(pkt, SERVER_ADDR)
            print(f"Sent data: \"{messages[next_seq]}\", with seq:{next_seq}")
            next_seq += 1
        #
        # Wait for ACK
        sock.settimeout(TIMEOUT)
        try:
            data, addr = sock.recvfrom(RECV_BUFFER)
        except socket.timeout:
            print("Timeout waiting for ACK; resending window")
            for r in range(send_base, next_seq):
                packet = create_packet(r, 0, DATA_FLAG, CLIENT_RWND, messages[r])
                sock.sendto(packet, SERVER_ADDR)
        #
        packet = parse_packet(data)
        if not packet:
            continue
        #
        r_seq, r_ack, r_flags, r_rwnd, r_payload = packet
        #
        if r_flags & ACK_FLAG:
            print(f"← ACK for seq = {r_ack}")
            send_base = r_ack + 1

            if send_base == next_seq:
                pass

            continue


    print("\nAll data sent successfully.\n")

    #
    # Send fin packet to start closing
    fin_packet = create_packet(0, 0, FIN_FLAG, CLIENT_RWND, b"")
    sock.sendto(fin_packet, SERVER_ADDR)
    print("Sent FIN")
    fin_sent = True

    #
    # Wait for server to send ack
    while True:
        try:
            data, addr = sock.recvfrom(RECV_BUFFER)
        except socket.timeout:
            print("Timed out while waiting for server's FIN-ACK. resending FIN message")
            sock.sendto(fin_packet, SERVER_ADDR)
            continue

        #
        # got the packet
        packet = parse_packet(data)
        if not packet:
            continue

        seq, ack, flags, recv_rwnd, payload = packet

        if (flags & ACK_FLAG) and fin_sent:
            print("Received ACK for FIN. Now a final Fin from the server is needed to close connection.")
            break

    while True:
        try:
            data, addr = sock.recvfrom(RECV_BUFFER)
        except socket.timeout:
            print("Waiting for server FIN")
            continue

        packet = parse_packet(data)
        if not packet:
            continue

        seq, ack, flags, recv_rwnd, payload = packet

        if flags & FIN_FLAG:
            print("Received server Fin")
            break

    # Step 4: final ACK back to server
    final_ack = create_packet(0, seq + 1, ACK_FLAG, CLIENT_RWND, b"")
    sock.sendto(final_ack, SERVER_ADDR)
    print("Sent final ACK\n Connection Closed")

    return


if __name__ == "__main__":
    start_client()