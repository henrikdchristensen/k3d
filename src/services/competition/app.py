import os
import requests
from flask import Flask
from waitress import serve
from flask_cors import CORS
from flask import jsonify, request
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
from werkzeug import exceptions
from models import Competition
from database import (
    put_competition,
    get_competitions,
    get_competition_by_id,
    get_competitions_active,
    put_competition_user,
    get_competitions_users,
    get_competition_users,
    get_user_competitions,
    get_leaderboard as get_leaderboard_db,
    get_competition_leaderboard as get_competition_leaderboard_db,
    get_challenge_leaderboard as get_challenge_leaderboard_db,
    delete_submissions as delete_submissions_db,
    delete_submissions_where as delete_submissions_where_db,
    put_submission,
    get_submissions,
    get_submissions_challenge_user,
    update_competition
)
from utils import get_challenges, authorize, validate_json_fields

app = Flask(__name__)

CORS(app)

def read_secret(secret_name):
    with open(f"/var/secrets/{secret_name}.txt", "r") as f:
        return f.readline()

mode = os.getenv("KUBERNETES_MODE")

# config for jwt
if mode == "in-cluster":
    #TODO_HC:
    app.config['SECRET_KEY'] = 'y2Z2."1el=eo'
    app.config["JWT_SECRET_KEY"] = '7P7f(fM8}!,)'
    # app.config['SECRET_KEY'] = read_secret("JWT_SecretKey")
    # app.config["JWT_SECRET_KEY"] = read_secret("JWT_JWTSecretKey")
else:
    app.config['SECRET_KEY'] = 'y2Z2."1el=eo'
    app.config["JWT_SECRET_KEY"] = '7P7f(fM8}!,)'

app.config['JWT_TOKEN_LOCATION'] = ['headers']

# JWT Initialization
jwt = JWTManager(app)

@app.get("/")
def hello_world():
    """Exist only to make the app seem healthy for the gateway"""
    return "Hello World!", 200


@app.put('/competitions/<competition_id>')
@jwt_required()
@authorize(["admin"])
@validate_json_fields(["name", "active"])
def update_competitions(competition_id):
    """Updates all fields for a given competition"""
    data = request.get_json()
    """Retrieve competition from id using database"""
    competition = get_competition_by_id(competition_id)
    if not competition:
        raise exceptions.NotFound(f"Competition with id: {competition_id} not found")
    
    competition.name= data["name"]
    competition.active = data["active"]

    updated_competition = update_competition(competition)
    return updated_competition.serialize(), 200

@app.get('/competitions')
@jwt_required()
@authorize(["admin"])
def list_competitions():
    """Get all competitions"""
    competitions = get_competitions()

    #Get the challenges in relationship with each competition
    competition_ids = [competition.id for competition in competitions]
    competitions_dict = [competition.serialize() for competition in competitions]
    for competition in competitions_dict:
        competition["challenges"] = []

    challenges = get_challenges(competition_ids)

    for challenge in challenges:
        for competition in competitions_dict:
            if challenge["competition_id"] == competition["id"]:
                competition["challenges"].append(challenge)

    return jsonify(competitions_dict), 200

@app.get('/competitions/<competition_id>')
def get_specific_competition(competition_id):
    """Get a specific competition with the given id"""
    competition = get_competition_by_id(competition_id)
    if competition is None:
        raise exceptions.BadRequest('The competition was not found or does not exist.')

    challenges = get_challenges([competition.id])
    competition_dict = competition.serialize()
    competition_dict['challenges'] = challenges

    return jsonify(competition_dict), 200

@app.get('/competitions/active')
def list_active_competitions():
    """Get all active competitions"""
    competitions = get_competitions_active()

    competition_ids = [competition.id for competition in competitions]
    competitions_dict = [competition.serialize() for competition in competitions]
    for competition in competitions_dict:
        competition["challenges"] = []

    challenges = get_challenges(competition_ids)
    for challenge in challenges:
        for competition in competitions_dict:
            if challenge["competition_id"] == competition["id"]:
                competition["challenges"].append(challenge)

    return jsonify(competitions_dict), 200

'''Competition end points'''
@app.post('/competitions')
@jwt_required()
@authorize(["admin"])
@validate_json_fields(["name", "active"])
def create_competition():
    """Create a new competition"""
    data = request.get_json()
    new_competition = Competition(name=data['name'], active=data['active'])
    created_competition = put_competition(new_competition)
    if created_competition is None:
        raise exceptions.BadRequest('The competition could not be created.')
    return jsonify(new_competition.serialize()), 201

'''Participants end points'''
@app.post('/participants')
@jwt_required()
@authorize(["user", "developer"])
@validate_json_fields(["competition_id"])
def add_participant():
    """Sign up user to competition"""
    username = get_jwt_identity()
    data = request.get_json()
    
    created_participation = put_competition_user(username, data['competition_id'])

    if created_participation is None:
        raise exceptions.BadRequest('The user could not be signed up.')
    
    return jsonify(created_participation), 201

@app.get('/participants/<username>')
def get_specific_participant_competitions(username):
    """Get all competition of specific user"""
    competition_participants = get_user_competitions(username)
    return [competition_participant for competition_participant in competition_participants], 200

@app.get('/participants')
@jwt_required()
def list_competitions_participants():
    """Get all competitions and their participants"""
    claims = get_jwt()
    if claims["role"] != "admin":
        raise exceptions.Forbidden("Only admins can get all competitions with their participants")
    competition_participants = get_competitions_users()
    return [competition_participant for competition_participant in competition_participants], 200

@app.get('/participants/<competition_id>')
def get_specific_competition_participants(competition_id):
    """Get all participants of specific competition"""
    competition_participants = get_competition_users(competition_id)
    return [competition_participant for competition_participant in competition_participants], 200

'''Leaderboard endpoints'''
@app.get("/leaderboards")
def get_leaderboard():
    scores = get_leaderboard_db()
    return [score for score in scores], 200

@app.get("/leaderboards/competition/<competition_id>")
def get_competition_leaderboard(competition_id):
    scores = get_competition_leaderboard_db(competition_id)
    return [score for score in scores], 200

@app.get("/leaderboards/challenge/<challenge_id>")
def get_challenge_leaderboard(challenge_id):
    scores = get_challenge_leaderboard_db(challenge_id)
    return scores, 200

@app.delete("/submissions")
@jwt_required()
@authorize(["admin"])
def delete_submissions():
    """Delete all submissions"""
    data = request.get_json()

    valid_fields = ['username', 'competition_id', 'challenge_id', 'admin']

    # Validate input
    for f in data.keys():
        if f not in valid_fields:
            raise exceptions.BadRequest(f"{f} not a valid field")

    try:
        message = delete_submissions_where_db(data) if data is not None else delete_submissions_db()
    except Exception as e:
        raise exceptions.BadRequest(500, description=f"An error occurred while resetting the leaderboard: {str(e)}")

    return jsonify(message), 200

'''Score endpoints'''
@app.put("/update-score")
@jwt_required()
@authorize(["admin"])
@validate_json_fields(["username","competition_id","challenge_id","score"])
def update_score():
    data = request.get_json()
    try:
        """Inserting log submission - insertion set up to timestamp it now utc zone"""
        message = put_submission(data["username"], data["competition_id"], data["challenge_id"], "Admin added this", data["score"], True, False) # Adjusted to avoid confusion
    except Exception as e:
        raise exceptions.BadRequest(f"An error occurred while updating the score: {str(e)}")
    return jsonify(message), 200

'''Challenge service communication endpoints'''
@app.post("/add-challenge")
@jwt_required()
@authorize(["admin"])
@validate_json_fields(["competition_id","challenge_id"])
def add_ctf():
    data = request.get_json()
    
    if mode == "in-cluster":
        ctf_endpoint = "http://service-ctf/add-comp"
    else:
        ctf_endpoint = "http://localhost:8081/add-comp"
    
    response = requests.post(ctf_endpoint, json=data)

    if response.status_code != 201:
        raise exceptions.NotFound("Unknown error happened")
    
    return f'The challenge {data["challenge_id"]} has been successfully added to the comp {data["competition_id"]}', 201

@app.get("/submissions")
@jwt_required()
@authorize(["admin"])
def list_submissions():
    """Get all submissions"""
    submissions = get_submissions()
    return [submission for submission in submissions], 200

@app.get("/submissions/challenges/<challenge_id>")
@jwt_required()
def list_submissions_by_challenge(challenge_id):
    """Get all submissions"""
    claims = get_jwt()
    submissions = get_submissions_challenge_user(challenge_id, claims["sub"])
    return [submission for submission in submissions], 200

#TODO: have this been tested?
@app.post("/submit")
@jwt_required()
@authorize(["user", "developer"])
@validate_json_fields(["competition_id","challenge_id", "flag"])
def submit_flag():
    """Endpoint should let players submit a flag for a challenge for a competition"""
    """Endpoint checks flag validity using the ctf-service"""
    """Endpoint ensures logging of the submission"""
    data = request.get_json()
    username = get_jwt_identity()
    
    competition_id = data.get("competition_id")
    challenge_id = data.get("challenge_id")
    flag = data.get("flag")

    request_body = {
        "challenge_id": challenge_id,
        "flag": flag
    }

    if mode == "in-cluster":
        ctf_endpoint = "http://service-ctf/evaluate"
    else:
        ctf_endpoint = "http://localhost:8081/evaluate"
    
    response = requests.post(ctf_endpoint, json=request_body)
    response_body = response.json()

    if response.status_code == 404:
        raise exceptions.NotFound("Challenge not found")
    
    score = response_body.get("score")

    """Inserting log submission - insertion set up to timestamp it now utc zone"""
    put_submission(username, competition_id, challenge_id, flag, score, False, True if score > 0 else False)

    return jsonify(
        {
        "message": "Submission has been logged",
        "new_score": score
        }
    ), 200


if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=8080)