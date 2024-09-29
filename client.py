import sys
import os
import socket

class Client:
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

        code = int(received.split(":")[2])

        match code:
            case -1:
                print(f"Error: User {username} already logged in")
            case 0:
                print(f"Welcome {username}")
            case 1:
                print(f"Error: User {username} not found")
            case 2:
                print(f"Error: Wrong password for user {username}")

    def received_badauth(self) -> None:
        print("Error: You must be logged in to perform this action")

    def roomlist(self) -> None:
        mode = input(
                "Would you like to join as a player or viewer? [PLAYER/VIEWER] "
                )

        self.socket.send(f"ROOMLIST:{mode}".encode())

        response = self.socket.recv(8192).decode()

        if response == "ROOMLIST:ACKSTATUS:1":
            sys.stderr.write("ClientError: Please input a valid mode")
            return

        if response == "BADAUTH":
            self.received_badauth()
            return
        
        roomlist = response.split(":")[-1]

        print(f"Room available to join as {mode}: {roomlist}")

    def talk_to_server(self) -> None:
        while True:
            data = input("> ")
            match data:
                case "LOGIN":
                    self.login()

                case "REGISTER":
                    self.register()

                case "ROOMLIST":
                    self.roomlist()

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

        response = self.socket.recv(8192).decode()

        if response[:-1] != "REGISTER:ACKSTATUS:":
            raise Exception("Recieved invalid response for register: " + response)

        response_code = int(response[-1])

        match response_code:
            case 0:
                print(f"Successfully created user account {username}")
            case 1:
                print(f"Error: User {username} already exists")

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
