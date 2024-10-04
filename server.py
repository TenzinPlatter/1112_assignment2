import sys
import time
import socket
import os
import bcrypt
import json
from threading import Thread
from config import Config
import globals

class Client:
    def __init__(self, sock: socket.socket) -> None:
        self.socket = sock
        self.account = None

    def close(self):
        if self.account:
            self.account.logout()

        self.account = None
        self.socket.close()

    def has_auth(self) -> bool:
        return self.account is not None

    def get_name(self) -> str | None:
        """
        Returns None if user is not logged in, else returns username
        """
        if not self.account:
            return None

        return self.account.get_name();

    def try_login(self, args: list[str]) -> None:
        """
        Scans data sent by connection until LOGIN message is sent with valid login
        details
        Pass in user_input as whole input without any cleaning
        """
        if len(args) != 2:
            self.socket.send("LOGIN:ACKSTATUS:3".encode())
            return

        account = globals.logins.try_login(args[0], args[1])

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

        if globals.logins.account_exists(username):
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
        
        roomlist = ",".join(globals.rooms.get_room_names(mode == "PLAYER"))        

        self.socket.send(f"ROOMLIST:ACKSTATUS:0:{roomlist}".encode())

    def check_for_badauth(self) -> bool:
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
        
        if globals.rooms.room_exists(room_name):
            self.socket.send("CREATE:ACKSTATUS:2".encode())
            return

        if globals.rooms.server_is_full():
            self.socket.send("CREATE:ACKSTATUS:3".encode())
            return
        
        globals.rooms.create(room_name)
        self.socket.send("CREATE:ACKSTATUS:0".encode())

    def join_room(self, args: list[str]) -> None:
        if len(args) != 2:
            self.socket.send("JOIN:ACKSTATUS:3".encode())
            return

        room_name, mode = args

        if mode not in ["PLAYER", "VIEWER"]:
            self.socket.send("JOIN:ACKSTATUS:3".encode())
            return

        if not globals.rooms.room_exists(room_name):
            self.socket.send("JOIN:ACKSTATUS:1".encode())
            return

        if globals.rooms.game_is_full(room_name):
            self.socket.send("JOIN:ACKSTATUS:2".encode())
            return

        if self.account is None:
            raise Exception(
                    "How has this happened - should've been caught by badauth"
                    )

        globals.rooms.join(room_name, self.account.name, mode == "PLAYER")

        self.socket.send("JOIN:ACKSTATUS:0".encode())


class Server:
    clients = []

    def __init__(self, config: Config) -> None:
        Server.config = config
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        host, port = "127.0.0.1", config.get_port()
        self.socket.bind((host, port))
        self.socket.listen()

        print(
              f"Server started on ip {host}, port {port}, awaiting connection..."
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
                if client.check_for_badauth():
                    return

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
        globals.logins.add_account(name, hash.decode())

        with open(Server.config.get_userdatabase_path(), "w") as f:
            json.dump(accounts, f, indent = 4)

    # TODO: remove for submission
    def close(self):
        for client in self.clients:
            client.close()

        time.sleep(1)

        self.socket.close()
        os._exit(0)

def main(args: list[str]) -> None:
    if len(args) != 1:
        sys.stderr.write("Error: Expecting 1 argument <server config path>.\n")
        os._exit(1)

    # sets all users and checks for config errors
    config = Config(args[0])

    Server(config).listen()

if __name__ == "__main__":
    main(sys.argv[1:])
