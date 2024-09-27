import sys
import socket
from threading import Thread
from logins import Logins

class Client:
    def __init__(self, sock: socket.socket) -> None:
        self.socket = sock
        self.account = None

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

        account = Logins.try_login(data[0], data[1])

        if isinstance(account, int):
            self.socket.send(f"LOGIN:ACKSTATUS:{account}".encode())
            return

        self.account = account
        # indicates successful login
        self.socket.send("LOGIN:ACKSTATUS:0".encode())

class Server:
    clients = []
    rooms = []

    def __init__(self, host: str, port: int) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))
        self.socket.listen()

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
        Broadcasts a message to all other members in server
        If all_but is set to False, the message will be sent to the clients
        passed in, else sent to all clients other than the ones passed in
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

            if msg.startswith("LOGIN:"):
                client.try_login(msg)

def main(args: list[str]) -> None:
    Server("127.0.0.1",  8002).listen()

if __name__ == "__main__":
    main(sys.argv[1:])
