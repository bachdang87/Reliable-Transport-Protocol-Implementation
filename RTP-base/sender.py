import argparse
import socket
import sys

from utils import PacketHeader, compute_checksum


def sender(receiver_ip, receiver_port, window_size):
    """TODO: Open socket and send message from sys.stdin."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Thiết lập timeout 500ms theo đúng đặc tả của project
    s.settimeout(0.5) 
    
    # Đọc toàn bộ dữ liệu (sử dụng encode để chuyển thành bytes)
    data = sys.stdin.read().encode('utf-8')
    
    packets = []
    
    # 1. Tạo gói START (type=0, seq_num=0)
    start_hdr = PacketHeader(type=0, seq_num=0, length=0)
    start_hdr.checksum = compute_checksum(start_hdr / b"")
    packets.append(start_hdr / b"")
    
    # 2. Phân mảnh dữ liệu thành các gói DATA (type=2)
    seq = 1
    MAX_PAYLOAD = 1456  # 1472 (max UDP) - 16 (PacketHeader)
    for i in range(0, len(data), MAX_PAYLOAD):
        chunk = data[i:i+MAX_PAYLOAD]
        hdr = PacketHeader(type=2, seq_num=seq, length=len(chunk))
        hdr.checksum = compute_checksum(hdr / chunk)
        packets.append(hdr / chunk)
        seq += 1
        
    # 3. Tạo gói END (type=1)
    end_hdr = PacketHeader(type=1, seq_num=seq, length=0)
    end_hdr.checksum = compute_checksum(end_hdr / b"")
    packets.append(end_hdr / b"")
    
    total_packets = len(packets)
    base = 0
    next_to_send = 0
    
    # 4. Vòng lặp Sliding Window
    while base < total_packets:
        # Gửi các gói tin nằm trong giới hạn của window
        while next_to_send < base + window_size and next_to_send < total_packets:
            s.sendto(bytes(packets[next_to_send]), (receiver_ip, receiver_port))
            next_to_send += 1
            
        try:
            # Chờ nhận ACK
            ack_pkt, _ = s.recvfrom(2048)
            if len(ack_pkt) < 16:
                continue
                
            ack_hdr = PacketHeader(ack_pkt[:16])
            
            # Xác thực checksum của gói ACK nhận được
            expected_checksum = ack_hdr.checksum
            ack_hdr.checksum = 0
            if expected_checksum != compute_checksum(ack_hdr / b""):
                continue  # Bỏ qua nếu checksum không khớp
                
            # Xử lý Cumulative ACK (type=3)
            if ack_hdr.type == 3:
                # Nếu ACK yêu cầu seq_num lớn hơn base hiện tại, trượt window lên
                if ack_hdr.seq_num > base:
                    base = ack_hdr.seq_num
                    
        except socket.timeout:
            # Nếu đã gửi gói END (base đang ở vị trí cuối) và timeout 500ms, có thể an toàn thoát
            if base == total_packets - 1:
                break
            else:
                # Retransmit toàn bộ các gói trong window hiện tại chưa được ACK
                for i in range(base, next_to_send):
                    s.sendto(bytes(packets[i]), (receiver_ip, receiver_port))


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

    sender(args.receiver_ip, args.receiver_port, args.window_size)


if __name__ == "__main__":
    main()
