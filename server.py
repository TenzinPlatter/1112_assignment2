import sys
import time
import socket
import os
import bcrypt
import json
from threading import Thread
from room import Room, Rooms
from logins import Logins

class Client:
    def __init__(self, sock: socket.socket) -> None:
        self.socket = sock
        self.account = None

    @property
    def name(self) -> str | None:
        """
        Returns None if user is not logged in, else returns username
        """
        if not self.account:
            return None

        return self.account.name

    def close(self):
        if self.account:
            self.account.logout()

        self.account = None
        self.socket.close()

    def has_auth(self) -> bool:
        return self.account is not None

    def try_login(self, args: list[str]) -> None:
        """
        Scans data sent by connection until LOGIN message is sent with valid login
        details
        Pass in user_input as whole input without any cleaning
        """
        if len(args) != 2:
            self.socket.send("LOGIN:ACKSTATUS:3".encode())
            return

        account = Server.logins.try_login(args[0], args[1])

        if isinstance(account, int):
            self.socket.send(f"LOGIN:ACKSTATUS:{account}".encode())
            return

        self.account = account
        # indicates successful login
        self.socket.send("LOGIN:ACKSTATUS:0".encode())

    def try_register(self, args: list[str]) -> None:
        if len(args) != 2:
            self.socket.send("REGISTER:ACKSTATUS:2".encode())

        username, password = args

        if Server.logins.account_exists(username):
            self.socket.send("REGISTER:ACKSTATUS:1".encode())
            return

        Server.register_account(username, password)
        self.socket.send("REGISTER:ACKSTATUS:0".encode())

    def roomlist(self, args: list[str]) -> None:
        if (
                len(args) != 1
                or (mode := args[0]) not in ["PLAYER", "VIEWER"]
                ):
            self.socket.send("ROOMLIST:ACKSTATUS:1".encode())
            return
        
        roomlist = ",".join(Server.rooms.get_room_names(mode == "PLAYER"))        

        self.socket.send(f"ROOMLIST:ACKSTATUS:0:{roomlist}".encode())

    def handle_for_badauth(self) -> bool:
        """
        Returns true if client is unauthorized, else false. Handles sending
        BADAUTH message
        """
        if not self.has_auth():
            self.socket.send("BADAUTH".encode())
            return True
        return False
    
    def create_room(self, args: list[str]):
        #TODO: need someway to check if this is a ':' in the name of room vs
        # a separator
        if len(args) != 1:
            self.socket.send("CREATE:ACKSTATUS:4".encode())
            return

        room_name = args[0]

        # checks for that room name contains only alphanumeric, '-', ' ' or '_'
        # characters and has length is no greater than 20
        if not (
                room_name
                .replace("-", "")
                .replace(" ", "")
                .replace("_", "")
                .isalnum()
                or len(room_name) > 20
                ):
            self.socket.send("CREATE:ACKSTATUS:1".encode())
            return
        
        if Server.rooms.room_exists(room_name):
            self.socket.send("CREATE:ACKSTATUS:2".encode())
            return

        if Server.rooms.server_is_full():
            self.socket.send("CREATE:ACKSTATUS:3".encode())
            return
        
        Server.rooms.create(room_name)
        self.socket.send("CREATE:ACKSTATUS:0".encode())

    def join_room(self, args: list[str]) -> None:
        if len(args) != 2:
            self.socket.send("JOIN:ACKSTATUS:3".encode())
            return

        room_name, mode = args

        if mode not in ["PLAYER", "VIEWER"]:
            self.socket.send("JOIN:ACKSTATUS:3".encode())
            return

        if not Server.rooms.room_exists(room_name):
            self.socket.send("JOIN:ACKSTATUS:1".encode())
            return

        if mode == "PLAYER" and Server.rooms.game_is_full(room_name):
            self.socket.send("JOIN:ACKSTATUS:2".encode())
            return

        # mostly so lsp stops yelling
        if self.account is None:
            raise Exception(
                    "How has this happened - should've been caught by badauth"
                    )

        Server.rooms.join(room_name, self.account.name, mode == "PLAYER")
        self.socket.send("JOIN:ACKSTATUS:0".encode())

        room = Server.rooms.get_room(room_name)

        if room.game_is_full() and not room.in_progress:
            self.socket.send("GAME:1".encode())
            Server.play_game(room)
            return

        if room.in_progress:
            self.socket.send("GAME:2".encode())
            self.send_in_progress_message(room)
            return

        self.socket.send("GAME:0".encode())

    def send_in_progress_message(self, room: Room) -> None:
        # index of player whos turn it is
        i = 1 - room.cross_turn
        self.socket.send(
                f"INPROGRESS:{room.players[i]}:{room.players[i - 1]}"
                .encode()
                )

class Server:
    clients: list[Client] = []
    rooms = Rooms()
    logins = Logins()

    def __init__(self, config) -> None:
        Server.config = config

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        host, port = "127.0.0.1", config.get_port()
        self.socket.bind((host, port))

        self.socket.listen()

        print(
              f"Server started on ip {host}, port {port}, awaiting connection..."
              )

    @staticmethod
    def play_game(room: Room) -> None:
        players: list[Client] = []

        for client in Server.clients:
            client.socket.send(
                    f"BEGIN:{room.players[0]}:{room.players[1]}"
                    .encode()
                    )

            if client.name in room.players:
                players.append(client)

        if players[0].name != room.players[0]:
            players.reverse()
        
        game_over = False
        while not game_over:
            # index of player who is currently having their turn
            i = 1 - room.cross_turn

            # assumes will recieve PLACE message
            data = players[i].socket.recv(8192).decode()

            if not data:
                msg = f"GAMEEND:{room.get_board_status()}:2:{players[1 - i]}"
                map(lambda c : c.socket.send(msg.encode()), Server.clients)
                return

            x, y = map(lambda x : int(x), data.split(":")[1:])

            # alternates turn in this method
            room.make_move(x, y)
            if (code := room.check_for_game_end()):
                msg = f"GAMEEND:{room.get_board_status()}:{code - 1}"

                # game won
                if code == 1:
                    msg += room.players[i]

                map(lambda c : c.socket.send(msg.encode()), Server.clients)
                return
                

            board_status: str = room.get_board_status()
            for client in Server.clients:
                client.socket.send(
                        f"BOARDSTATUS:{board_status}"
                        .encode()
                        )

    def listen(self) -> None:
        """
        Listens for connections and spawns a thread for each one
        """
        while True:
            conn, addr = self.socket.accept()
            print("Connection from: ", addr)

            client = Client(conn)

            Server.clients.append(client)

            # starts client in new thread
            Thread(target = self.handle_new_client, args = (client,)).start()

    def handle_new_client(self, client: Client):
        """
        Function to handle client on a thread
        """
        while True:
            msg = client.socket.recv(8192).decode()
            cmd = msg.split(":")[0]
            args = msg.split(":")[1:]

            # commands requiring authorisation
            if cmd in ["ROOMLIST", "CREATE", "JOIN"]:
                if client.handle_for_badauth():
                    continue

            match cmd:
                case "LOGIN":
                    client.try_login(args)

                case "REGISTER":
                    client.try_register(args)

                case "ROOMLIST":
                    client.roomlist(args)

                case "CREATE":
                    client.create_room(args)

                case "JOIN":
                    client.join_room(args)

                case "QUIT":
                    self.close()

    @staticmethod
    def register_account(name: str, password: str) -> None:
        hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        new_account = {
                "username" : name,
                "password" : hash.decode()
                }

        with open(Server.config.get_userdatabase_path(), "r") as f:
            accounts = json.load(f)

        accounts.append(new_account)
        Server.logins.add_account(name, hash.decode())

        with open(Server.config.get_userdatabase_path(), "w") as f:
            json.dump(accounts, f, indent = 4)

    # TODO: remove for submission
    def close(self):
        for client in self.clients:
            client.close()

        time.sleep(1)

        self.socket.close()
        os._exit(0)


class Config:
    @staticmethod
    def is_valid_user_json(user: dict) -> bool:
        return (
                user.keys() == ["username", "password"]
                or user.keys() == ["password", "username"]
                )

    def __init__(self, config_path: str) -> None:
        self.parse_config(os.path.expanduser(config_path))
        self.parse_users()

        port = self.get_port()

        if not isinstance(port, int) or not (1024 <= port <= 65535):
            sys.stderr.write(
                    "Invalid port, expecting an integer in range 1024-65535\n"
                             )
            os._exit(0)

    def get_userdatabase_path(self) -> str:
        return os.path.expanduser(self.config["userDatabase"])

    def get_port(self) -> int:
        return int(self.config["port"])

    def parse_users(self) -> None:
        user_config = os.path.expanduser(self.config["userDatabase"])
        try:
            with open(user_config, 'r') as f:
                users = json.load(f)
                if not isinstance(users, list):
                    raise TypeError

                for user in users:
                    Config.is_valid_user_json(user)
                    Server.logins.add_account(user["username"], user["password"])

        except FileNotFoundError:
            sys.stderr.write(
                f"Error: {user_config} doesn't exist.\n"
                )
            os._exit(1)

        except json.JSONDecodeError:
            sys.stderr.write(
                    f"Error: {user_config} is not in a valid JSON format.\n"
                    )
            os._exit(1)

        # json is not a list
        except TypeError:
            sys.stderr.write(
                    f"Error: {user_config} is not a JSON array.\n"
                    )
            os._exit(1)

    def parse_config(self, config_path: str) -> None:
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)

        except FileNotFoundError:
            sys.stderr.write("Error: {config_path} doesn't exist.\n")
            os._exit(1)

        except json.JSONDecodeError:
            sys.stderr.write(
                    f"Error: {config_path} is not in a valid JSON format.\n"
                    )
            os._exit(1)

        expected_keys = ["port", "userDatabase"]
        missing_keys = []

        for key in expected_keys:
            if key not in self.config:
                missing_keys.append(key)

        if missing_keys:
            sys.stderr.write(
                    f"Error: {config_path} missing key(s): {', '.join(missing_keys)}\n"
                    )
            os._exit(1)

def main(args: list[str]) -> None:
    if len(args) != 1:
        sys.stderr.write("Error: Expecting 1 argument <server config path>.\n")
        os._exit(1)

    # sets all users and checks for config errors
    config = Config(args[0])

    Server(config).listen()

if __name__ == "__main__":
    main(sys.argv[1:])
