import os
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_apscheduler import APScheduler
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
from werkzeug import exceptions
from waitress import serve
from models import Challenge
from database import *
from kubernetes import client, utils
import kubernetes
from utils import *
import json
import ast
from flask_cors import CORS

mode = os.getenv("KUBERNETES_MODE", "local")
print(f"Kubernetes mode: {mode}")

app = Flask(__name__)

CORS(app)

scheduler = APScheduler()
def read_secret(secret_name):
    with open(f"/var/secrets/{secret_name}.txt", "r") as f:
        return f.readline()

# config for jwt
if mode == "in-cluster":
    app.config['SECRET_KEY'] = read_secret("JWT_SecretKey")
    app.config["JWT_SECRET_KEY"] = read_secret("JWT_JWTSecretKey")
else:
    app.config['SECRET_KEY'] = 'y2Z2."1el=eo'
    app.config["JWT_SECRET_KEY"] = '7P7f(fM8}!,)'

app.config['JWT_TOKEN_LOCATION'] = ['headers']

# JWT Initialization
jwt = JWTManager(app)

@scheduler.task('interval', id='stop_test_instances', seconds=10)
def stop_test_instances():
    """Stops test instances which have been running for more than 10 minutes"""
    # TODO add the checking of the time ran of the kubernetes challenge-test instances.
    print("Running scheduled job")
    load_kubernetes_config()
    v1 = client.CoreV1Api()
    custom_client = client.CustomObjectsApi()
    result = v1.list_namespaced_pod( "project", label_selector="mode=test",watch=False)
    for pod in result.items:
        status = pod.status.phase    
        container_status = pod.status.container_statuses[0]
        difference = datetime.now(timezone.utc) - container_status.state.running.started_at
        if container_status.started is False or container_status.ready is False:
            waiting_state = container_status.state.waiting
            if waiting_state.message is not None and 'Error' in waiting_state.message:
                status = waiting_state.reason
                difference = datetime.now(timezone.utc) - datetime.now(timezone.utc)
                #Calculate actual age
        if difference.total_seconds() > 600:
            print("terminating" + pod.metadata.name + "and service and route")
            #Generating the correct names
            namespace = "project"
            pod_name = pod.metadata.name
            service_name = "svc-" + pod_name[4:]
            route_name = "rt-" + pod_name[4:]
            print(pod_name)
            print(service_name)
            print(route_name)
            
            # Delete the Pod
            try:
                v1.delete_namespaced_pod(pod_name, namespace)
            except kubernetes.client.exceptions.ApiException as e:
                if e.status == 404:
                    print(f"Pod {pod_name} not found.")
                else:
                    raise e

            # Delete the Service
            try:
                v1.delete_namespaced_service(service_name, namespace)
            except kubernetes.client.exceptions.ApiException as e:
                if e.status == 404:
                    print(f"Service {service_name} not found.")
                else:
                    raise e

            # Delete the HTTPRoute
            try:
                custom_client.delete_namespaced_custom_object(
                    group="gateway.networking.k8s.io",
                    version="v1",
                    namespace=namespace,
                    plural="httproutes",
                    name=route_name,
                )
            except kubernetes.client.exceptions.ApiException as e:
                if e.status == 404:
                    print(f"HTTPRoute {route_name} not found.")
                else:
                    raise e
        
        print(pod.metadata.name + " " + status + " " + str(container_status.state.running.started_at) + " age:" + str(difference.total_seconds()))

    return ""


@app.get("/")
def hello_world():
    """Exist only to make the app seem healthy for the gateway"""
    return "Hello World!", 200


@app.post("/challenges")
@validate_file_fields(['name', 'description', 'category', 'difficulty', 'flag_format', 'author', 'flag', 'resource_limits', 'score'])
@validate_form_fields(['image_url'])
@jwt_required()
@authorize(["developer"])
def create_challenge(file):
    """Creates a new Challenge, expects an URL and a YAML file with configuration"""

    #file_two = request.files["file"]
    #print(file_two)
    #conf_two = yaml.safe_load(file_two)
    #print(conf_two)
    data = json.loads(request.form.get("data"))

    # Create Challenge object
    #try:
    challenge = Challenge(
        "",
        file["name"],
        file["description"],
        file["category"],
        file["difficulty"],
        file["flag_format"],
        file["author"],
        file["flag"],
        file["resource_limits"],
        file["score"],
        False,
        False,
        data["image_url"],
        None
    )
    #except:
    #    raise exceptions.BadRequest("Error reading .yaml config")

    insert_challenge(challenge)

    return (
        f"Challenge with id '{challenge.id}' and name '{challenge.name}' created successfully",
        201,
    )


# TODO: Maybe only available for testing?
@app.get("/challenges")
@jwt_required()
@authorize(["admin"])
def get_challenges():
    """Get all Challenges from the database"""
    challenges = [challenge.serialize() for challenge in read_challenges()]
    if len(challenges) == 0:
        raise exceptions.NotFound("No Challenges found")
    return challenges, 200

@app.get("/challenges/author/<username>")
@jwt_required()
@authorize(["developer","admin"])
def get_challenges_by_author(username):
    """Get all Challenges from the database with auther = username"""
    challenges = [challenge.serialize() for challenge in read_challenges_from_author(username)]
    return challenges, 200

@app.get("/challenges/active")
@jwt_required()
def get_active_challenges():
    """Get the active Challenges for the given user, if admin returns all active challenges"""
    claims = get_jwt()
    active_instances = get_active_instances(claims)
    return active_instances, 200

@app.get("/challenges/<challenge_id>")
@jwt_required()
def get_challenge(challenge_id):
    """Get Challenge with given id"""
    return read_challenge(challenge_id).serialize(), 200

# TODO: Maybe should be a PATCH request, if we only want to update some of the fields?
@app.put("/challenges/<challenge_id>")
@validate_file_fields(['name', 'description', 'category', 'difficulty', 'flag_format', 'author', 'flag', 'resource_limits', 'score'])
@validate_form_fields(['image_url'])
@jwt_required()
@authorize(["developer"])
def put_challenge(challenge_id, file):
    """Updates Challenge with given id"""
    conf = file
    data = json.loads(request.form.get("data"))


    # Creating the Challenge object
    # try:
    challenge = Challenge(
        challenge_id,
        conf["name"],
        conf["description"],
        conf["category"],
        conf["difficulty"],
        conf["flag_format"],
        conf["author"],
        conf["flag"],
        conf["resource_limits"],
        conf["score"],
        False,
        False,
        data["image_url"],
        None
    )
    # except:
    #    raise exceptions.BadRequest("Error reading yaml configuration")

    update_challenge(challenge)

    return f"Challenge with id '{challenge_id}' updated successfully", 200


@app.patch("/challenges/<challenge_id>")
def patch_challenge(challenge_id):
    """Used to update only some of the fields in Challenges"""
    data = request.get_json(silent=True) or {}
    valid_fields = ['name', 'description', 'category', 'difficulty', 'flag_format', 'author', 'flag', 'resource_limits', 'score', 'image_url']
    
    for f in data.keys():
        if f not in valid_fields:
            raise exceptions.BadRequest(f"{f} not a valid field")
    
    try:
        patch_update_challenge(challenge_id, data)
        return f"Challenge with id {challenge_id} patched successfully", 200
    except exceptions.NotFound:
        raise exceptions.NotFound(f"Challenge with id {challenge_id} not found")


@app.delete("/challenges/<challenge_id>")
@jwt_required()
@authorize(["admin", "developer"])
def delete_challenge(challenge_id):
    """Deletes Challenge with given id, incl. all active instances!"""
    try:
        remove_challenge(challenge_id)
        return f"Challenge with id {challenge_id} deleted successfully", 200
    except exceptions.NotFound:
        raise exceptions.NotFound(f"Challenge with id {challenge_id} not found")


@app.get("/open/<challenge_id>")
@jwt_required()
@authorize(["user", "developer"])
def open_challenge(challenge_id):
    """Opens an instance of the challenge with the given id, for the currently logged in User, if the user does not have too many instances open already"""
    # Sketch of what needs to be done
    username = get_jwt_identity()
    challenge = read_challenge(challenge_id)

    # Check the namespace of that idenfier
    load_kubernetes_config()

    # Check that the user does not have to many instances running.
    k8s_client = client.ApiClient()
    DYNAMIC_CLIENT = kubernetes.dynamic.DynamicClient(
        kubernetes.client.api_client.ApiClient()
    )

    resources = ast.literal_eval(challenge.resource_limits)

    # Create the pod
    pod_dict = generate_pod_dict(challenge_id, username, challenge.image_url, resources["resources"], "production", challenge.name)
    utils.create_from_dict(k8s_client, pod_dict)

    # Create the Service for the Pod
    service_dict = generate_service_dict(challenge_id, username, "production", challenge.name)
    utils.create_from_dict(k8s_client, service_dict)

    # Create the HTTPRoute
    route_dict = generate_route_dict(challenge_id, username, "production", challenge.name)
    apply_simple_item(DYNAMIC_CLIENT, route_dict)

    return "Challenge is opened", 200


@app.get("/close/<challenge_id>")
@jwt_required()
def close_challenge(challenge_id):
    """Removes the pod, service and httproute associated with the given challenge_id and username"""
    username = get_jwt_identity()
    namespace = "project"

    # Set up kubernetes
    load_kubernetes_config()
    v1 = client.CoreV1Api()
    custom_client = client.CustomObjectsApi()

    pod_name = "ctf-" + str(challenge_id) + "-" + username
    service_name = "svc-" + str(challenge_id) + "-" + username

    # Delete the Pod
    try:
        v1.delete_namespaced_pod(pod_name, namespace)
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"Pod {pod_name} not found.")
        else:
            raise e

    # Delete the Service
    try:
        v1.delete_namespaced_service(service_name, namespace)
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"Service {service_name} not found.")
        else:
            raise e

    # Delete the HTTPRoute
    try:
        custom_client.delete_namespaced_custom_object(
            group="gateway.networking.k8s.io",
            version="v1",
            namespace=namespace,
            plural="httproutes",
            name="rt-" + str(challenge_id) + "-" + username,
        )
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"HTTPRoute rt-{challenge_id}-{username} not found.")
        else:
            raise e

    return "Challenge is closed", 200


# TODO: Pretty hard to find a good way to remove the networking stuff after 10 min.
@app.get("/test/<challenge_id>")
@jwt_required()
@authorize(["admin", "developer"])
def test_challenge(challenge_id):
    """Spawns an instance of the given challenge in test mode, meaning it will only be active for 10 min."""

    # TODO add a lot of checks, eg check if teh challenge is marked for testing.

    username = get_jwt_identity()
    challenge = read_challenge(challenge_id)

    # Check the namespace of that idenfier test
    load_kubernetes_config()

    # Check that the user does not have to many instances running.
    k8s_client = client.ApiClient()
    DYNAMIC_CLIENT = kubernetes.dynamic.DynamicClient(
        kubernetes.client.api_client.ApiClient()
    )

    resources = ast.literal_eval(challenge.resource_limits)

    # Create the pod
    pod_dict = generate_pod_dict(challenge_id, username, challenge.image_url, resources["resources"], "test", challenge.name)
    utils.create_from_dict(k8s_client, pod_dict)

    # Create the Service for the Pod
    service_dict = generate_service_dict(challenge_id, username, "test", challenge.name)
    utils.create_from_dict(k8s_client, service_dict)

    # Create the HTTPRoute
    route_dict = generate_route_dict(challenge_id, username, "test", challenge.name)
    apply_simple_item(DYNAMIC_CLIENT, route_dict)

    return "Challenge is opened in testing mode", 200


"""The following 3 endpoints has been agreed to be internal only"""

@app.post('/evaluate')
@validate_json_fields(["challenge_id", "flag"])
def evaluate_flag():
    """This should retrieve the challenge_id from the request body and check in the database if the flag is valid or not"""
    """The endpoint should return the score, that is 0 if invalid or score if correct"""
    data = request.get_json()
    challenge_id = data.get("challenge_id")
    flag = data.get("flag")

    try:
        challenge = read_challenge(challenge_id)
    except exceptions.NotFound as e:
        raise exceptions.NotFound(f"Challenge with id {challenge_id} is not found")
    
    score = challenge.score if challenge.flag==flag else 0
    return jsonify({
        "score": score
    }), 200


@app.post("/add-comp")
@jwt_required()
@authorize(["admin"])
@validate_json_fields(["challenge_ids", "competition_id"])
def add_comp():
    """Sets the competition_id for the given challenges"""
    data = request.get_json()
    challenge_ids = data["challenge_ids"]

    updated_challenges = add_challenges_to_competition(tuple(challenge_ids), data["competition_id"])

    return {
        "message": f"succesfully added challenges {challenge_ids} to competition {data["competition_id"]}",
        "updated_challenges": [challenge.serialize() for challenge in updated_challenges]
    },201

@app.post("/challenges/competitions")
@validate_json_fields(["competition_ids"])
def get_challenges_competitions():
    data = request.get_json()
    competition_ids = data["competition_ids"]
    try:
        challenges = [challenge.serialize() for challenge in read_challenges_from_competitions(tuple(competition_ids))]
    except Exception as e:
        print(e)
        raise exceptions.BadRequest(f"an error occured")

    return challenges, 200

@app.get("/challenges/competitions/<competition_id>")
def get_challenge_competition(competition_id):
    """Get the challenges based on the competition id and if they are active based on username"""
    try:
        challenges = [challenge.serialize() for challenge in read_challenges_from_competitions((competition_id,))]
    except Exception as e:
        print(e)
        raise exceptions.BadRequest(f"an error occured")

    return challenges, 200

#TBD admins should displays all active instances of all Challenge's


if __name__ == "__main__":
    if mode == "in-cluster":
        scheduler.init_app(app)
        scheduler.start()
    serve(app, host='0.0.0.0', port=8081)


