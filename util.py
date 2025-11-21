import struct
import random
import time

SERVER_IP = '127.0.0.1'
SERVER_PORT = 8080

MAX_PAYLOAD = 512
HEADER_SIZE = 15

SYN_FLAG = 1
ACK_FLAG = 2
FIN_FLAG = 4
DATA_FLAG = 8

def compute_checksum(data):
    seq, ack, flags, rwnd, length, = struct.unpack("!IIBHH", data[:HEADER_SIZE-2])
    payload = data[:HEADER_SIZE-2:]
    checksum = 0
    #
    for i in range(0, len(data), 2):
        add = (data[i] << 8)
        if i + 1 < len(data):
            add |= data[i+1]

        checksum += add
        #
        # wrap if needed
        checksum = (checksum & 0xFFFF) + (checksum >> 16)

    return checksum

def create_packet(seq, ack, flags, rwnd, payload):
    header_field = struct.pack("!IIBHH", seq, ack, flags, rwnd, len(payload))
    checksum_field = compute_checksum(header_field + payload)
    #
    return header_field + struct.pack("!H", checksum_field) + payload


def parse_packet(data):
    if len(data) < HEADER_SIZE:
        return None
    #
    # unpack the packet
    seq, ack, flags, rwnd, length, checksum = struct.unpack("!IIBHHH", data[:HEADER_SIZE])
    payload = data[HEADER_SIZE:]
    checksum_removed = struct.pack("!IIBHH",seq,ack,flags,rwnd,length) + payload
    #
    # check if the checksum is correct
    computed_checksum = compute_checksum(checksum_removed)
    if computed_checksum != checksum:
        print(f"ERROR: Checksum from packet: ${checksum} does not match computed: ${computed_checksum}")
        return None
    #
    return seq, ack, flags, rwnd, payload