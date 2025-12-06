#include <iostream>
#include <cstring>
#include <cstdlib>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

const int PORT = 4242;
const int BUFFER_SIZE = 1024;

int main() {
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);
    char buffer[BUFFER_SIZE] = {0};
    const char *hello = "Hello from server";

    // 1. Create socket file descriptor
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("socket failed");
        exit(EXIT_FAILURE);
    }

    // Optional: Forcefully attach socket to the port 8080
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT, &opt, sizeof(opt))) {
        perror("setsockopt failed");
        exit(EXIT_FAILURE);
    }

    // 2. Define server address
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY; // Listen on all available interfaces
    address.sin_port = htons(PORT);

    // 3. Bind the socket to port 8080
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("bind failed");
        exit(EXIT_FAILURE);
    }

    // 4. Listen for incoming connections (up to 3 in queue)
    if (listen(server_fd, 3) < 0) {
        perror("listen failed");
        exit(EXIT_FAILURE);
    }

    std::cout << "Server listening on port " << PORT << std::endl;

    // 5. Accept an incoming client connection
    if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t*)&addrlen)) < 0) {
        perror("accept failed");
        exit(EXIT_FAILURE);
    }
    
    std::cout << "Connection accepted" << std::endl;

    // 6. Read data from client
    ssize_t bytes_read = recv(new_socket, buffer, BUFFER_SIZE - 1, 0);
    if (bytes_read < 0) {
        perror("recv failed");
    } else {
        buffer[bytes_read] = '\\0'; // Ensure null-termination
        std::cout << "Client message: " << buffer << std::endl;
    }
    

    // 7. Send data to the client
    send(new_socket, hello, strlen(hello), 0);
    std::cout << "Server sent 'Hello' message to client" << std::endl;

    // 8. Close the connection sockets
    close(new_socket);
    close(server_fd);
    std::cout << "Connections closed. Server shutting down." << std::endl;

    return 0;
}
