class Room:
    def __init__(self, name: str) -> None:
        self.name: str = name
        self._players: list[str] = []
        self._viewers: list[str] = []

    def game_is_full(self) -> bool:
        return len(self._players) >= 2
    
    def join_game(self, player_name: str, as_player: bool) -> None:
        if as_player and len(self._players) >= 2:
            raise Exception("Only try to join game as player if game is not full")

        if as_player:
            self._players.append(player_name)

        else:
            self._viewers.append(player_name)

class Rooms:
    def __init__(self) -> None:
        self._rooms: list[Room] = []

    def create(self, name: str) -> None:
        if self.is_full():
            raise Exception("Only create a room after checking that server is not full")

        self._rooms.append(Room(name))

    def get_room_names(self, is_player: bool) -> list[str]:
        if is_player:
            return [room.name for room in self._rooms if not room.game_is_full()]

        return [room.name for room in self._rooms]

    def room_exists(self, room_name: str) -> bool:
        for room in self._rooms:
            if room.name == room_name:
                return True

        return False

    def is_full(self) -> bool:
        return len(self._rooms) >= 256
