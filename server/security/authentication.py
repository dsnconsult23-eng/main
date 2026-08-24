from config import Config

class Authenticator:
    def __init__(self):
        self.valid_users = {
            Config.SERVICE_USER: Config.SERVICE_PASSWORD
        }

    def authenticate(self, username: str, password: str) -> bool:
        return self.valid_users.get(username) == password