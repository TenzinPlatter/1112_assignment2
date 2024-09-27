class Login:
    def __init__(self, name: str, password: str) -> None:
        self._name = name
        self._password = password
        self._logged_in = False
    
    def is_valid(self, name: str, password: str) -> bool:
        if self._name == name and self._password == password:
            self._logged_in = True
            return True

        return False

    def logout(self) -> None:
        self._logged_in = False

    def get_name(self) -> str:
        return self._name

class Logins:
    _accounts = []

    @staticmethod
    def add_account(name: str, password: str) -> None:
        Logins._accounts.append(Login(name, password))

    """
    Returns a Login obj for a successful login, or 
    1 -> Username Not found
    2 -> Only Username matches
    """
    @staticmethod
    def try_login(name: str, password: str) -> Login | int:
        for account in Logins._accounts:
            if account.valid_details(name, password):
                return account

            if account.get_name() == name:
                return 2
        
        return 1

