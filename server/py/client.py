import socket

def tcp_client():
    host = '127.0.0.1'  # Server IP address
    port = 65432        # Server port

    # Create a TCP/IP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Connect to the server
        s.connect((host, port))
        
        # Send data
        //message = 'Hello, Server!'
        //s.sendall(message.encode())
        
        # Receive response
        data = s.recv(1024)
        print('Received', repr(data.decode()))

if __name__ == "__main__":
    tcp_client()