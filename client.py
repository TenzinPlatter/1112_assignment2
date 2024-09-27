import sys
import os
import socket
from threading import Thread

class Client:
    def __init__(self, host: str, port: int) -> None:
        self.socket = socket.socket()
        self.socket.connect((host, port))
        self.name = input("Enter your name: ")

        self.talk_to_server()

    def handle_login(self) -> None:
        username = input("Enter username: ")
        password = input("Enter password: ")
        
        if not username or not password:
            return

        self.socket.send(f"LOGIN:{username}:{password}".encode())

        received = self.socket.recv(8192).decode()

        code = int(received.split(":")[2])

        match code:
            case 0:
                print(f"Welcome {username}")
            case 1:
                print(f"Error: User {username} not found")
            case 2:
                print(f"Error: Wrong password for user {username}")

    def talk_to_server(self) -> None:
        self.socket.send(self.name.encode())
        Thread(target = self.receive_message).start()
        self.send_message()

    def send_message(self) -> None:
        while True:
            data = input()
            if data == "LOGIN":
                self.handle_login()
                return

            self.socket.send(data.encode())
    
    def receive_message(self) -> None:
        while True:
            msg = self.socket.recv(1024).decode()
            if not msg.strip():
                os._exit(1)

def main(args: list[str]) -> None:
    if len(args) != 2:
        sys.stderr.write(
                "Error: Expecting 2 arguments: <server address> <port>\n"
                )
        os._exit(1)

    try:
        Client(args[0], int(args[1]))
    except ConnectionRefusedError:
        sys.stderr.write(
                f"Error: cannot connect to server at {args[0]} and {args[1]}.\n"
                )


if __name__ == "__main__":
    main(sys.argv[1:])
