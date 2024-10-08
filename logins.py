import bcrypt

class Login:
    def __init__(self, name: str, password: str) -> None:
        self.name = name
        self._password = password
        self._logged_in = False

    def __str__(self) -> str:
        return f"Name: '{self.name}', Password: '{self._password}'"
    
    def is_valid(self, name: str, password: str) -> int:
        """
        returns 1 if valid, 0 if not, and -1 if account is valid but already
        logged in
        """
        if (
                self.name == name
                and bcrypt.checkpw(password.encode(), self._password.encode())
                ):
            if self._logged_in:
                return -1

            return 1

        return 0

    def logout(self) -> None:
        self._logged_in = False

class Logins:
    def __init__(self) -> None:
        self.accounts: list[Login] = []

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
            if account.name == name:
                return True

        return False

    def try_login(self, name: str, password: str) -> Login | int:
        """
        Returns a Login obj for a successful login, or 
        -1 -> Account already logged in
        1 -> Username Not found
        2 -> Only Username matches
        """
        for account in self.accounts:
            code = account.is_valid(name, password)
            if code == 1:
                account._logged_in = True
                return account

            if code == -1:
                return -1

        if self.account_exists(name):
            return 2
        
        return 1
