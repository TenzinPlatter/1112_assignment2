import sys
import os
import socket
import game
from threading import Thread
from queue import Queue

class Client:
    def __init__(self, host: str, port: int) -> None:
        self.socket = socket.socket()
        self.socket.connect((host, port))
        self.in_game = False
        self.username = None
        self.responses = Queue()

        Thread(target = self.talk_to_server).start()
        self.listen_to_server()

    def listen_to_server(self) -> None:
        while True:
            responses = self.socket.recv(8192).decode().split("\n")
            print(responses)

            for response in responses:
                if response.startswith("BEGIN"):
                    self.in_game = True
                    Thread(
                            target = self.handle_game_start,
                            args = (response, )
                            ).start()
                    continue
                
                if response.strip():
                    self.responses.put(response)

    def talk_to_server(self) -> None:
        print("Enter 'help' to see a list of commands")
        while True:
            if self.in_game:
                continue

            command = input("> ").lower().strip()
            match command:
                case "clear":
                    os.system("clear")
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

    def login(self) -> None:
        info = self.get_info()

        if not info:
            return

        username, password = info

        self.socket.send(f"LOGIN:{username}:{password}".encode())

        received = self.responses.get()

        code = int(received.split(":")[2])

        match code:
            case -1:
                print(f"Error: User {username} already logged in")
            case 0:
                print(f"Welcome {username}")
                self.username = username
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

        response = self.responses.get()

        if response == "ROOMLIST:ACKSTATUS:1":
            sys.stderr.write("ClientError: Please input a valid mode")
            return

        if self.check_for_badauth(response):
            return
        
        roomlist = response.split(":")[-1]

        print(f"Rooms available to join as {mode.lower()}: {roomlist}")

    def create_room(self) -> None:
        room_name = input("Please enter a name for your room: ")
        self.socket.send(f"CREATE:{room_name}".encode())

        response = self.responses.get()

        if self.check_for_badauth(response):
            return

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
        else:
            sys.stderr.write("Invalid room mode, please use 'p' or 'v'.\n")
            return

        self.socket.send(f"JOIN:{room_name}:{mode}".encode())

        response = self.responses.get()
        
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

        response = self.responses.get()
        print(response)
        game_started = int(
                response
                .split(":")[1]
                )
        # GAME:0 -> not started
        # GAME:1 -> started

        if not game_started:
            return

    def handle_game_start(self, data: str) -> None:
        crosses, noughts = data.split(":")[1:]

        is_player = self.username in (crosses, noughts)
        crosses_turn = True

        board_status = "000000000"
        while True:
            game.print_board_from_status(board_status)
            move = None

            if is_player:
                if self.username == crosses:
                    if crosses_turn:
                        move = input("Please enter your move: [x y] ")
                    else:
                        print("Please wait for your opponent to make their move.")

                elif self.username == noughts:
                    if not crosses_turn:
                        move = input("Please enter your move: [x y] ")
                    else:
                        print("Please wait for your opponent to make their move.")
            else:
                msg = f"Match between {crosses} and {noughts} will commence"
                msg += f", it is currently {crosses}'s turn."
                print(msg)

            if move and move.lower() == "forfeit":
                self.socket.send("FORFEIT".encode())

            elif move:
                def valid_move(x, y):
                    pos = 3 * y + x
                    return 0 <= x <= 2 and 0 <= y <= 2 and board_status[pos] == "0"

                try:
                    x, y = map(lambda x : int(x), move.split())
                except:
                    # to trigger while loop on invalid input
                    x, y = -1, -1

                while not valid_move(x, y):
                    print("Sorry, that was an invalid move, please try again")
                    print("0 <= x, y <= 2")
                    move = input("Enter a valid coordinate in the form [x y] ")

                    try:
                        x, y = map(lambda x : int(x), move.split())
                    except:
                        x, y = -1, -1

                print("sending place")
                self.socket.send(f"PLACE:{x}:{y}".encode())

            data = self.responses.get()

            if data.startswith("GAMEEND:"):
                self.handle_game_end(data.split(":")[1:], is_player)
                return

            board_status = data.split(":")[1]
            crosses_turn = not crosses_turn

    def handle_game_in_progress(self, data: str) -> None:
        args = data.split(":")[1:]
        msg = f"Match between {args[0]} and {args[1]} is currently in"
        msg += f" progress, it is {args[0]}'s turn"
        print(msg)
        board_status = "000000000"
        while True:
            data = self.responses.get()

            if data.startswith("GAMEEND:"):
                self.handle_game_end(data.split(":")[1:], False)
                return

            board_status = data.split(":")[1]
            game.print_board_from_status(board_status)
    
    def handle_game_end(self, args: list[str], is_player: bool) -> None:
        code = int(args[1])
        
        if code == 0:
            winner = args[-1]
            if is_player:
                if self.username == winner:
                    print("Congratulations, you win!")
                else:
                    print("Sorry you lost. Good luck next time.")
            else:
                print(f"{winner} has won this game")

        elif code == 1:
            print("Game ended in a draw")

        if code == 2:
            winner = args[-1]
            print(f"{winner} won due to the opposing player forfeiting")


    def show_help(self) -> None:
        with open("help.txt", "r") as f:
            print(f.read())

    def register(self) -> None:
        info = self.get_info()

        if not info:
            return

        username, password = info

        self.socket.send(f"REGISTER:{username}:{password}".encode())

        response = self.responses.get()

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
