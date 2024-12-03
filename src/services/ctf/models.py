import uuid


class Challenge:
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        category: str,
        difficulty: str,
        flag_format: str,
        author: str,
        flag: str,
        resource_limits: dict,
        score: int,
        testing: bool,
        ready: bool,
        image_url: str,
        competition_id: str
    ) -> None:
        self.id = id if id != "" else str(uuid.uuid4())
        self.name = name
        self.description = description
        self.category = category
        self.difficulty = difficulty
        self.flag_format = flag_format
        self.author = author
        self.flag = flag
        self.resource_limits = resource_limits
        self.score = score
        self.testing = testing
        self.ready = ready
        self.image_url = (
            image_url if image_url != "" else "ghcr.io/knative/helloworld-go:latest"
        )
        self.competition_id = competition_id

    def __repr__(self) -> str:
        return f"<id:{self.id}, name:{self.name}, description:{self.description}, category:{self.category}, difficulty:{self.difficulty}, flag_format:{self.flag_format}, author:{self.author}, flag:{self.flag}, resource_limits:{self.resource_limits}, score:{self.score}, testing:{self.testing}, ready:{self.ready}, image_url:{self.image_url}, comp_id:{self.competition_id}>"

    def serialize(self) -> dict:
        """Function to convert this object to dict"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "difficulty": self.difficulty,
            "flag_format": self.flag_format,
            "author": self.author,
            "flag": self.flag,
            "resource_limits": self.resource_limits,
            "score": self.score,
            "testing": self.testing,
            "ready": self.ready,
            "image_url": self.image_url,
            "competition_id": self.competition_id,
        }
