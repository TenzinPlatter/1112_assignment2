import sys
import os
import socket
from threading import Thread class Client:
    def __init__(self, host: str, port: int) -> None:
        self.socket = socket.socket()
        self.socket.connect((host, port))

        self.talk_to_server()

    def login(self) -> None:
        info = self.get_info()

        if not info:
            return

        username, password = info

        self.socket.send(f"LOGIN:{username}:{password}".encode())

        received = self.socket.recv(8192).decode()

        print("received")

        code = int(received.split(":")[2])

        match code:
            case 0:
                print(f"Welcome {username}")
            case 1:
                print(f"Error: User {username} not found")
            case 2:
                print(f"Error: Wrong password for user {username}")

    def talk_to_server(self) -> None:
        Thread(target = self.receive_message).start()
        self.send_message()

    def send_message(self) -> None:
        while True:
            data = input("> ") match data:
                case "LOGIN":
                    self.login()

                case "REGISTER":
                    self.register()

                # delete for submission
                case "exit":
                    self.socket.send("QUIT".encode())
                    os._exit(0)

    def register(self) -> None:
        info = self.get_info()

        if not info:
            return

        username, password = info

        self.socket.send(f"REGISTER:{username}:{password}".encode())

    def get_info(self) -> tuple[str, str] | None:
        username = input("Enter username: ")
        password = input("Enter password: ")
        
        if not username:
            sys.stderr.write("Username cannot be empty.\n")
            return None

        if not password:
            sys.stderr.write("Password cannot be empty.\n")
            return None

        return (username, password)

    
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
