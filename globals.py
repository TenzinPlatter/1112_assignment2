from logins import Logins
from room import Rooms

def init():
    global _logins
    global _rooms

    _logins = Logins()
    _rooms = Rooms()

def logins():
    return _logins

def rooms():
    return _rooms
