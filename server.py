import sys
import socket
from threading import Thread

class Client:
    def __init__(self, name: str, sock: socket.socket) -> None:
        self.name = name
        self.socket = sock

class Server:
    clients = []

    def __init__(self, host: str, port: int) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))

        # pass in max number of clients
        self.socket.listen()
        print("Server waiting for connection...")

    """
    Listens for connections and spawns a thread for each one
    """
    def listen(self) -> None:
        while True:
            conn, addr = self.socket.accept()
            print("Connection from: ", addr)

            name = conn.recv(8192).decode()
            client = Client(name, conn)

            self.broadcast(name, name + " has joined the chat!")

            Server.clients.append(client)
            # starts client in new thread
            Thread(target = self.handle_new_client, args = (client,)).start()

    """
    Broadcasts a message to all other members in server
    """
    def broadcast(self, sender: str, msg: str):
        for client in Server.clients:
            if client.name == sender:
                continue

            client.socket.send(msg.encode())

    """
    Function to handle client on a thread
    """
    def handle_new_client(self, client: Client):
        while True:
            msg = client.socket.recv(1024).decode()

            # empty message means closed connection
            if not msg or msg == client.name + ": LEAVE":
                self.broadcast(
                        (client.name), f"{client.name} has left the chat!"
                        )
                Server.clients.remove(client)
                client.socket.close()
                break

            self.broadcast(client.name, msg)



def main(args: list[str]) -> None:
    Server("127.0.0.1",  8002).listen()


if __name__ == "__main__":
    main(sys.argv[1:])
