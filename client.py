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

    def check_for_badauth(self, response: str) -> bool:
        if response == "BADAUTH":
            print("Error: You must be logged in to perform this action")
            return True

        return False

    def roomlist(self) -> None:
        mode = input("Would you like to join as a player or viewer? [p/v] ")

        if mode == "p":
            mode = "PLAYER"
        elif mode == "v":
            mode = "VIEWER"

        self.socket.send(f"ROOMLIST:{mode}".encode())

        response = self.socket.recv(8192).decode()

        if response == "ROOMLIST:ACKSTATUS:1":
            sys.stderr.write("ClientError: Please input a valid mode")
            return

        if self.check_for_badauth(response):
            return
        
        roomlist = response.split(":")[-1]

        print(f"Rooms available to join as {mode}: {roomlist}")

    def create_room(self) -> None:
        room_name = input("Please enter a name for your room: ")
        self.socket.send(f"CREATE:{room_name}".encode())

        response = self.socket.recv(8192).decode()
        if not response[:-1] == "CREATE:ACKSTATUS:":
            raise Exception(f"Invalid response: {response}")

        code = int(response[-1])

        match code:
            case 0:
                print(f"Successfully created room {room_name}")
            case 1:
                print(f"Error Room {room_name} is invalid")
            case 2:
                print(f"Error: Room {room_name} already exists")
            case 3:
                print("Error: Server already contains a maxumum of 256 rooms")
            case _:
                raise Exception(f"Invalid return code {code}")

    def join_room(self) -> None:
        room_name = input("What room would you like to join? ")
        mode = input("Would you like to join as a player or viewer? [p/v] ")

        if mode == "p":
            mode = "PLAYER"
        elif mode == "v":
            mode = "VIEWER"

        self.socket.send(f"JOIN:{room_name}:{mode}".encode())

        response = self.socket.recv(8192).decode()
        
        if self.check_for_badauth(response):
            return

        if response[:-1] != "JOIN:ACKSTATUS:":
            raise Exception(f"Invalid response: {response}")

        code = int(response[-1])

        match code:
            case 0:
                print(f"Successfully joined room {room_name} as a {mode.lower()}")
            case 1:
                print(f"Error: No room named {room_name}")
            case 2:
                print(f"Error: The room {room_name} already has 2 players")

    def talk_to_server(self) -> None:
        print("Enter 'help' to see a list of commands")
        while True:
            command = input("> ").lower()
            match command:
                # delete for submission
                case "exit":
                    self.socket.send("QUIT".encode())
                    os._exit(0)

                case "help":
                    self.show_help()

                case "login":
                    self.login()

                case "register":
                    self.register()

                case "roomlist":
                    self.roomlist()

                case "create":
                    self.create_room()

                case "join":
                    self.join_room()

    def show_help(self) -> None:
        with open("help.txt", "r") as f:
            print(f.read())

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
