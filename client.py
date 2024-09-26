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

    def talk_to_server(self) -> None:
        self.socket.send(self.name.encode())
        Thread(target = self.receive_message).start()
        self.send_message()

    def send_message(self) -> None:
        while True:
            data = input()
            msg = f"{self.name}: {data}"
            self.socket.send(msg.encode())
    
    def receive_message(self) -> None:
        while True:
            msg = self.socket.recv(1024).decode()
            if not msg.strip():
                os._exit(1)

            print("\033[1;31;40m" + msg + "\033[0m")



def main(args: list[str]) -> None:
    Client("127.0.0.1", 8002)


if __name__ == "__main__":
    main(sys.argv[1:])
