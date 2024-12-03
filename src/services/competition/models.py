class Competition:
    def __init__(self, name: str, active: bool, id: str = None) -> None:
        self.id = id
        self.name = name
        self.active = active

    def __repr__(self) -> str:
        return f'<id:{self.id}, name:{self.name}, active:{self.active}>'

    def serialize(self) -> dict:
        '''Function to convert this object to dict'''
        return {
            'id': self.id,
            'name': self.name,
            'active': self.active
        }