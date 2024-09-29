import bcrypt

class Login:
    def __init__(self, name: str, password: str) -> None:
        self._name = name
        self._password = password
        self._logged_in = False

    def __str__(self) -> str:
        return f"Name: '{self._name}', Password: '{self._password}'"
    
    def is_valid(self, name: str, password: str) -> bool:
        if (
                self._name == name
                and bcrypt.checkpw(password.encode(), self._password.encode())
                ):
            self._logged_in = True
            return True

        return False

    def logout(self) -> None:
        self._logged_in = False

    def get_name(self) -> str:
        return self._name

class Logins:
    def __init__(self) -> None:
        self.accounts = []

    def __str__(self) -> str:
        res = ""
        for acc in self.accounts:
            res += str(acc) + ", "
        return res.rstrip(", ")

    def add_account(self, name: str, password: str) -> None:
        """
        takes password as str hash
        """
        self.accounts.append(Login(name, password))

    def account_exists(self, name: str) -> bool:
        """
        returns wether or not a username has an associated account
        """
        for account in self.accounts:
            if account.get_name() == name:
                return True

        return False

    def try_login(self, name: str, password: str) -> Login | int:
        """
        Returns a Login obj for a successful login, or 
        1 -> Username Not found
        2 -> Only Username matches
        """
        for account in self.accounts:
            if account.is_valid(name, password):
                return account

        if self.account_exists(name):
            return 2
        
        return 1
