import argparse
import socket
import sys

from utils import PacketHeader, compute_checksum


def receiver(receiver_ip, receiver_port, window_size):
    """TODO: Listen on socket and print received message to sys.stdout."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((receiver_ip, receiver_port))
    
    expected_seq = 0
    buffer = {}  # Dictionary để lưu các gói tin out-of-order
    
    while True:
        # Receive packet; address includes both IP and port
        pkt, address = s.recvfrom(2048)

        if len(pkt) < 16:
            continue

        # Extract header and payload
        pkt_header = PacketHeader(pkt[:16])
        msg = pkt[16 : 16 + pkt_header.length]

        # Verify checksum
        pkt_checksum = pkt_header.checksum
        pkt_header.checksum = 0
        computed_checksum = compute_checksum(pkt_header / msg)
        if pkt_checksum != computed_checksum:
            continue
            
        seq_num = pkt_header.seq_num
        pkt_type = pkt_header.type

        # Bỏ qua gói START nếu đang ở giữa kết nối (expected_seq > 0)
        if pkt_type == 0 and expected_seq > 0:
            continue
            
        # Xử lý gói START đầu tiên
        if pkt_type == 0 and expected_seq == 0:
            expected_seq = 1
            
        # Xử lý gói tin đến đúng thứ tự mong đợi
        elif seq_num == expected_seq:
            buffer[seq_num] = (pkt_type, msg)
            
            # Đọc và tăng expected_seq cho tất cả các gói tin liên tiếp đã được buffer
            while expected_seq in buffer:
                cur_type, cur_msg = buffer.pop(expected_seq)
                
                if cur_type == 2:  # Gói DATA
                    sys.stdout.write(cur_msg.decode('utf-8'))
                    sys.stdout.flush()
                elif cur_type == 1:  # Gói END
                    expected_seq += 1
                    # Gửi ACK cho gói END và thoát chương trình
                    ack_hdr = PacketHeader(type=3, seq_num=expected_seq, length=0)
                    ack_hdr.checksum = compute_checksum(ack_hdr / b"")
                    s.sendto(bytes(ack_hdr), address)
                    return
                    
                expected_seq += 1

        # Xử lý gói tin đến không đúng thứ tự (nhưng nằm trong window_size)
        elif expected_seq < seq_num < expected_seq + window_size:
            if seq_num not in buffer:
                buffer[seq_num] = (pkt_type, msg)
                
        # Các gói seq_num >= expected_seq + window_size sẽ bị drop tự động (không đưa vào buffer)
        
        # Gửi Cumulative ACK (yêu cầu seq_num tiếp theo mà receiver mong muốn)
        ack_hdr = PacketHeader(type=3, seq_num=expected_seq, length=0)
        ack_hdr.checksum = compute_checksum(ack_hdr / b"")
        s.sendto(bytes(ack_hdr), address)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "receiver_ip", help="The IP address of the host that receiver is running on"
    )
    parser.add_argument(
        "receiver_port", type=int, help="The port number on which receiver is listening"
    )
    parser.add_argument(
        "window_size", type=int, help="Maximum number of outstanding packets"
    )
    args = parser.parse_args()

    receiver(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()
