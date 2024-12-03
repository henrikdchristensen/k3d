import requests
from werkzeug import exceptions
from flask import request
from functools import wraps
from flask_jwt_extended import get_jwt
import os

mode = os.getenv("KUBERNETES_MODE")

def get_challenges(competition_ids):
    request_body = {
        "competition_ids": competition_ids
    }

    if mode == "in-cluster":
        ctf_endpoint = "http://service-ctf/challenges/competitions"
    else:
        ctf_endpoint = "http://localhost:8081/challenges/competitions"
    
    response = requests.post(ctf_endpoint, json=request_body)
    print(response)
    print("response should be printed before this")
    response_body = response.json()

    if response.status_code == 404:
        raise exceptions.NotFound("Challenge not found")

    return response_body

def validate_json_fields(fields):
    """Wrapper method to help validate json inputs"""
    def decorator(view_function):

        @wraps(view_function)
        def wrapper(*args, **kwargs):
            # get current request data
            data = request.get_json(silent=True) or {}

            for f in fields:
                if f not in data.keys():
                    raise exceptions.BadRequest(f"Error: missing parameter {f}")

            return view_function(*args, **kwargs)

        return wrapper
    return decorator

def authorize(allowed_roles):
    """Wrapper method to help validate json form inputs"""
    def decorator(view_function):

        @wraps(view_function)
        def wrapper(*args, **kwargs):
            # get current request data
            claims = get_jwt()
            if claims["role"] not in allowed_roles:
                raise exceptions.Forbidden(f"Denied, only {allowed_roles} allowed.")

            return view_function(*args, **kwargs)

        return wrapper
    return decorator