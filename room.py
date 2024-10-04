class Room:
    def __init__(self, name: str) -> None:
        self.name: str = name
        self.players: list[str] = []
        self.viewers: list[str] = []
        self.in_progress: bool = False
        self.cross_turn: bool = True

    def game_is_full(self) -> bool:
        return len(self.players) >= 2
    
    def join(self, player_name: str, as_player: bool) -> None:
        if as_player and len(self.players) >= 2:
            raise Exception("Only try to join game as player if game is not full")

        if as_player:
            self.players.append(player_name)

        else:
            self.viewers.append(player_name)

class Rooms:
    def __init__(self) -> None:
        self._rooms: list[Room] = []

    def join(self, room_name: str, username: str, as_player: bool) -> None:
        """
        Set as_player to true to join as a player, false to join as viewer
        """
        for room in self._rooms:
            if room.name == room_name:
                room.join(username, as_player)
                return

    def create(self, name: str) -> None:
        if self.server_is_full():
            raise Exception("Only create a room after checking that server is not full")

        self._rooms.append(Room(name))

    def get_room_names(self, is_player: bool) -> list[str]:
        if is_player:
            return [room.name for room in self._rooms if not room.game_is_full()]

        return [room.name for room in self._rooms]

    def get_room(self, room_name: str) -> Room:
        for room in self._rooms:
            if room.name == room_name:
                return room

        raise Exception("Only call after checking room exists")

    def room_exists(self, room_name: str) -> bool:
        for room in self._rooms:
            if room.name == room_name:
                return True

        return False

    def game_is_full(self, room_name: str) -> bool:
        for room in self._rooms:
            if room.name == room_name:
                return room.game_is_full()

        raise Exception("Should not be trying to check if a non existent room is full")

    def server_is_full(self) -> bool:
        return len(self._rooms) >= 256
