from flask import Flask, request
from waitress import serve
import json
import os
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
import datetime
from models import User
from werkzeug import exceptions
import bcrypt
from database import (
    insert_user,
    get_user,
    remove_user,
    update_user as update_user_db,
    read_users
)
from flask_cors import CORS

app = Flask(__name__)

CORS(app)

def read_secret(secret_name):
    with open(f"/var/secrets/{secret_name}.txt", "r") as f:
        return f.readline()

# config for jwt
if os.getenv("KUBERNETES_MODE") == "in-cluster":
    app.config['SECRET_KEY'] = read_secret("JWT_SecretKey")
    app.config["JWT_SECRET_KEY"] = read_secret("JWT_JWTSecretKey")
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

@app.post("/users")
@jwt_required(optional=True)
def add_user():
    """adds user to user database, based on request json body."""
    data = request.get_json()
    try:
        username = data["username"]
        password = data["password"]
        data_role = data["role"]
        email = data["email"]
    except:
        raise exceptions.BadRequest("Wrong JSON")
    if len(username) > 12:
        raise exceptions.BadRequest("Username is too long, max length is 12 characters")
    if data_role not in ["user","developer","admin"]:
        raise exceptions.BadRequest("Role not in accepted list of roles: user, developer or admin")
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    password_hashed = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    if get_user(username):
        raise exceptions.BadRequest("Username already taken, try another")
    elif data_role!="user" and not get_jwt_identity():
        raise exceptions.Forbidden("this action is only allowed by admins")
    elif get_jwt()["role"]!= "admin":
        raise exceptions.Forbidden("this action is only allowed by admins")
    else:
        insert_user(User(username, password_hashed, email, data_role))
        return f"Creation of user {username} succesful", 201

@app.delete("/users/<username>")
@jwt_required()
def delete_user(username):
    """removes the user with the given id. Admins or the specified user only"""
    my_username = get_jwt_identity()
    claims = get_jwt()
    if claims["role"] != "admin" and my_username != username:
        raise exceptions.BadRequest("only admins can remove other users")
    remove_user(username)
    return f"deletion of user {username} successful", 200

@app.patch("/update-name")
@jwt_required()
def update_name():
    """update name of user"""
    data = request.get_json()
    username = get_jwt_identity()
    user = get_user(username)
    if not user:
        raise exceptions.NotFound("Can't change name, user not found")
    old_name = user.username
    try:
        new_name = data["new_name"]
    except:
        raise exceptions.BadRequest("Wrong JSON")
    user.username = new_name
    update_user_db(user.username, user.password_hashed, user.email, user.role)
    return f"changed name of user {old_name} to {new_name}", 201


@app.patch("/update-password")
@jwt_required()
def update_password():
    """update password of user"""
    data = request.get_json()
    username = get_jwt_identity()
    user = get_user(username)
    if not user:
        raise exceptions.NotFound("Can't change password, user not found")
    try:
        new_password = data["new_password"]
    except:
        raise exceptions.BadRequest("Wrong JSON")
    new_password_bytes = new_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_new_password = bcrypt.hashpw(new_password_bytes, salt).decode('utf-8')
    user.password_hashed = hashed_new_password
    update_user_db(user.username, user.password_hashed, user.email, user.role)
    return f"changed password of user {user.username}", 201

@app.patch("/update-email")
@jwt_required()
def update_email():
    """update email of user"""
    data = request.get_json()
    username = get_jwt_identity()
    user = get_user(username)
    if not user:
        raise exceptions.NotFound("Can't change email, user not found")
    old_email = user.email
    try:
        new_email = data["new_email"]
    except:
        raise exceptions.BadRequest("Wrong JSON")
    user.email = new_email
    update_user_db(user.username, user.password_hashed, user.email, user.role)
    return f"changed email of user {user.username}, from {old_email} to {new_email}", 201
    
@app.post("/password-recovery")
@jwt_required()
def password_recovery():
    """Recover password. Will ask for your mail, and if correct, will log you in. You are now free to change your password."""
    data = request.get_json()
    username = get_jwt_identity()
    user = get_user(username)
    if not user:
        raise exceptions.NotFound("Can't recover password, user not found")
    try:
        email = data["email"]
    except:
        raise exceptions.BadRequest("Wrong JSON")
    if email != user.email:
        raise exceptions.BadRequest("Wrong email, not allowed to reset password")
    access_token = create_access_token(identity = user.username, expires_delta = datetime.timedelta(minutes = 60), additional_claims = {"role": user.role})
    return json.dumps({'message': 'Password recovery success, you are now logged in and can change your password', 'access_token': access_token}), 200

@app.patch("/users/<username>")
@jwt_required()
def update_user(username):
    claims = get_jwt()
    if claims["role"] != "admin":
        raise exceptions.Forbidden("This is the admin method to update users")
    data = request.get_json
    user = get_user(username)
    if "name" in data:
        user.name = data["name"]

    if "password" in data:
        password = data["password"]
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        user.password_hashed = bcrypt.hashpw(password_bytes, salt)

    if "email" in data:
        user.email = data["email"]

    if "role" in data:
        user.role = data["role"]
    update_user_db(user.username, user.password_hashed, user.email, user.role)
    return f"User {user.username} has been updated", 201

@app.post("/login")
def login():
    """login. A user provides username and password, and if they are both correct, they will get an access token in return."""
    data = request.get_json()
    try:
        username = data["username"]
        given_password = data["password"]
    except:
        raise exceptions.BadRequest("Wrong JSON")
    
    user = get_user(username)
    if not user:
        raise exceptions.NotFound("Can't login, user not found")
    given_password_bytes = given_password.encode('utf-8')
    storedPassword = user.password_hashed.encode('utf-8')
    if not bcrypt.checkpw(given_password_bytes, storedPassword):
        raise exceptions.BadRequest("Can't login, wrong password. stored: " + str(storedPassword) + "Given: " + str(given_password))
    # create access token that saves the user id as information in the token, and with a lifetime of 60 minutes
    access_token = create_access_token(identity = user.username, expires_delta = datetime.timedelta(minutes = 60), additional_claims = {"role": user.role})
    return json.dumps({'message': 'Login method success', 'access_token': access_token}), 200

@app.get("/users")
@jwt_required()
def get_all_users():
    """Get all users from the database"""
    claims = get_jwt()
    if claims["role"] != "admin":
        raise exceptions.Forbidden("only admins can get a list all users")
    users = [user.serialize() for user in read_users()]
    if len(users) == 0:
        raise exceptions.NotFound("No users found")
    return users, 200

# Method for testing
@app.post("/insert-admin")
def insert_admin():
    """insert admin user"""
    insert_user(User("admin1", bcrypt.hashpw("pass123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), "sejmail@gmail.com", "admin"))
    return f"admin has been added", 201

if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=8082)