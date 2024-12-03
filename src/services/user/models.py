class User:
    def __init__(self, username: str, password_hashed: str, email: str, role: str) -> None:
        self.username = username
        self.password_hashed = password_hashed
        self.email = email
        self.role = role
    
    def __repr__(self) -> str:
        return f'<User username:{self.username}, password_hashed:{self.password_hashed}, email:{self.email}, role:{self.role}>'
    
    def serialize(self) -> dict:
        """Function to convert this object to dict"""
        return {
            'username': self.username,
            'password_hashed': self.password_hashed,
            'email': self.email,
            'role': self.role
        }