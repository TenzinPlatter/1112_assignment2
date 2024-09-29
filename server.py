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

    def try_login(self, user_input: str) -> None:
        """
        Scans data sent by connection until LOGIN message is sent with valid login
        details
        Pass in user_input as whole input without any cleaning
        """
        data = user_input.split(":")

        if len(data) != 3:
            self.socket.send("LOGIN:ACKSTATUS:3".encode())
            return

        account = globals.logins.try_login(data[1], data[2])


        if isinstance(account, int):
            self.socket.send(f"LOGIN:ACKSTATUS:{account}".encode())
            return

        self.account = account
        # indicates successful login
        self.socket.send("LOGIN:ACKSTATUS:0".encode())

    def try_register(self, data: str) -> None:
        if len(data.split(":")) != 3:
            self.socket.send("REGISTER:ACKSTATUS:2".encode())

        username, password = data.split(":")[1:]

        if globals.logins.account_exists(username):
            self.socket.send("REGISTER:ACKSTATUS:1".encode())
            return

        Server.register_account(username, password)
        self.socket.send("REGISTER:ACKSTATUS:0".encode())

    def roomlist(self, data: str) -> None:
        if (
                len(data.split(":")) != 2
                or data.split(":")[1] not in ["PLAYER", "VIEWER"]
                ):
            self.socket.send("ROOMLIST:ACKSTATUS:1".encode())
            return

        if not self.has_auth():
            self.send_badauth()
            return
        
        roomlist = ",".join(globals.rooms.get_room_names())        

        self.socket.send(f"ROOMLIST:ACKSTATUS:0:{roomlist}".encode())

    def send_badauth(self):
        self.socket.send("BADAUTH".encode())

class Server:
    clients = []
    rooms = []

    def __init__(self, config: Config) -> None:
        Server.config = config
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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

    def broadcast(self, client_names: list[str], msg: str, all_but: bool = True):
        """
        Broadcasts a message to all other members in server If all_but is set to False, the message will be sent to the clients passed in, else sent to all clients other than the ones passed in
        """
        for client in Server.clients:
            if all_but and client.get_name() not in client_names:
                client.socket.send(msg.encode())
                continue

            if not all_but and client.get_name() in client_names:
                client.socket.send(msg.encode())
                continue

    def handle_new_client(self, client: Client):
        """
        Function to handle client on a thread
        """
        while True:
            msg = client.socket.recv(8192).decode()

            match msg:
                case s if s.startswith("LOGIN:"):
                    client.try_login(msg)

                case s if s.startswith("REGISTER:"):
                    client.try_register(msg)

                case s if s.startswith("ROOMLIST:"):
                    client.roomlist(msg)


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
