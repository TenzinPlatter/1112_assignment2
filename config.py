import json
import os
import sys
from globals import logins

def is_valid_user_json(user: dict) -> bool:
    return (
            user.keys() == ["username", "password"]
            or user.keys() == ["password", "username"]
            )

class Config:
    def __init__(self, config_path: str) -> None:
        self.parse_config(os.path.expanduser(config_path))
        self.parse_users()

        port = self.get_port()

        if not isinstance(port, int) or not (1024 <= port <= 65535):
            sys.stderr.write(
                    "Invalid port, expecting an integer in range 1024-65535\n"
                             )
            os._exit(0)

    def get_userdatabase_path(self) -> str:
        return os.path.expanduser(self.config["userDatabase"])

    def get_port(self) -> int:
        return int(self.config["port"])

    def parse_users(self) -> None:
        user_config = os.path.expanduser(self.config["userDatabase"])
        try:
            with open(user_config, 'r') as f:
                users = json.load(f)
                if not isinstance(users, list):
                    raise TypeError

                for user in users:
                    is_valid_user_json(user)
                    logins.add_account(user["username"], user["password"])

        except FileNotFoundError:
            sys.stderr.write(
                f"Error: {user_config} doesn't exist.\n"
                )
            os._exit(1)

        except json.JSONDecodeError:
            sys.stderr.write(
                    f"Error: {user_config} is not in a valid JSON format.\n"
                    )
            os._exit(1)

        # json is not a list
        except TypeError:
            sys.stderr.write(
                    f"Error: {user_config} is not a JSON array.\n"
                    )
            os._exit(1)

    def parse_config(self, config_path: str) -> None:
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)

        except FileNotFoundError:
            sys.stderr.write("Error: {config_path} doesn't exist.\n")
            os._exit(1)

        except json.JSONDecodeError:
            sys.stderr.write(
                    f"Error: {config_path} is not in a valid JSON format.\n"
                    )
            os._exit(1)

        expected_keys = ["port", "userDatabase"]
        missing_keys = []

        for key in expected_keys:
            if key not in self.config:
                missing_keys.append(key)

        if missing_keys:
            sys.stderr.write(
                    f"Error: {config_path} missing key(s): {', '.join(missing_keys)}\n"
                    )
            os._exit(1)

