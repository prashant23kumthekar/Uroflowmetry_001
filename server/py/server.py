import socket

def start_tcp_server(host='127.0.0.1', port=65432):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen()
        print(f'Server listening on {host}:{port}')
        
        conn, addr = server_socket.accept()
        with conn:
            print(f'Connected by {addr}')

            data = {5,7,8,11,13,7,19,23,29,22,19,17,13,11,7}
            print(f'Sending data: {data}')
            conn.sendall(str(data).encode())  # Echo back the received data

if __name__ == '__main__':
    start_tcp_server()