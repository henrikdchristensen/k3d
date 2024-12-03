from functools import wraps
from flask import request
import kubernetes
from werkzeug import exceptions
from flask_jwt_extended import get_jwt
from kubernetes import client, config, utils
import yaml
import json
import os

mode = os.getenv("KUBERNETES_MODE", "local")

def load_kubernetes_config():
    """Loads appropriate Kubernetes config based on environment (local or cloud)."""
    if mode == "in-cluster":
        config.load_incluster_config()
    else:
        # Path to shared kubeconfig file
        kubeconfig_path = os.environ.get("KUBECONFIG", "/k3s-config/k3s.yaml")
        k3s_server_hostname = os.environ.get("KUBE_HOST", "k3s-server")
        with open(kubeconfig_path, "r") as f:
            config_data = yaml.safe_load(f)
            # Update server field
            config_data['clusters'][0]['cluster'][
                'server'] = f"https://{k3s_server_hostname}:6443"
            kubeconfig_dict = config.kube_config.Configuration()
            config.load_kube_config_from_dict(
                config_data, client_configuration=kubeconfig_dict)
            client.Configuration.set_default(kubeconfig_dict)

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

def validate_file_fields(fields):
    """Wrapper method to help validate yaml file inputs, passes the file as 'file'"""
    def decorator(view_function):

        @wraps(view_function)
        def wrapper(*args, **kwargs):
            # get current request file
            if "file" not in request.files:
                raise exceptions.BadRequest("No file uploaded")

            file = request.files["file"]

            if file.filename == "":
                raise exceptions.BadRequest("No filename")

            if not file or not file.filename.rsplit(".", 1)[1].lower() in ["yaml", "yml"]:
                raise exceptions.BadRequest("Error: not a valid file format")

            print(file)
            conf = yaml.safe_load(file)
            print(conf)
            for f in fields:
                if f not in conf.keys():
                    raise exceptions.BadRequest(f"Error: missing file parameter: {f}")
                
            kwargs["file"] = conf

            return view_function(*args, **kwargs)

        return wrapper
    return decorator

def validate_form_fields(fields):
    """Wrapper method to help validate json form inputs"""
    def decorator(view_function):

        @wraps(view_function)
        def wrapper(*args, **kwargs):
            # get current request data
            data = json.loads(request.form.get("data"))

            for f in fields:
                if f not in data.keys():
                    raise exceptions.BadRequest("Error: missing parameter")

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

def apply_simple_item(
    dynamic_client: kubernetes.dynamic.DynamicClient,
    manifest: dict,
    verbose: bool = False,
):
    """Used to apply kubernetes manifests which are from CRD's"""
    api_version = manifest.get("apiVersion")
    kind = manifest.get("kind")
    resource_name = manifest.get("metadata").get("name")
    namespace = manifest.get("metadata").get("namespace")
    crd_api = dynamic_client.resources.get(api_version=api_version, kind=kind)

    try:
        crd_api.get(namespace=namespace, name=resource_name)
        crd_api.patch(body=manifest, content_type="application/merge-patch+json")
        if verbose:
            print(f"{namespace}/{resource_name} patched")
    except kubernetes.dynamic.exceptions.NotFoundError:
        crd_api.create(body=manifest, namespace=namespace)
        if verbose:
            print(f"{namespace}/{resource_name} created")

def generate_pod_dict(challenge_id, username, image, resources, mode, name):
    """Used to generate pod manifest in pythin dict form"""
    pod_dict = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "ctf-" + str(challenge_id) + "-" + username,
            "labels": {
                "ctf-id-username": "ctf-" + str(challenge_id) + "-" + username,
                "username": username,
                "challenge_id": challenge_id,
                "name": name,
                "mode": mode,
                "type": "ctf"},
            "namespace": "project",
        },
        "spec": {
            "containers": [
                {
                    "name": "ctf-" + str(challenge_id) + "-" + username,
                    "image": image,
                    "resources": resources,
                    "ports": [{"containerPort": 8080}],
                }
            ]
        },
    }
    return pod_dict

def generate_service_dict(challenge_id, username, mode, name):
    """Used to generate service manifest in pythin dict form"""
    service_dict = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "svc-" + str(challenge_id) + "-" + username,
            "labels": {
                "ctf-id-username": "ctf-" + str(challenge_id) + "-" + username,
                "username": username,
                "name": name,
                "challenge_id": challenge_id,
                "mode": mode},
            "namespace": "project",
        },
        "spec": {
            "selector": {"ctf-id-username": "ctf-" + str(challenge_id) + "-" + username},
            "type": "ClusterIP",
            "ports": [{"protocol": "TCP", "port": 80, "targetPort": 8080}],
        },
    }
    return service_dict

def generate_route_dict(challenge_id, username, mode, name):
    """Used to generate service manifest in pythin dict form"""
    route_dict = {
        "apiVersion": "gateway.networking.k8s.io/v1",
        "kind": "HTTPRoute",
        "metadata": {
            "name": "rt-" + str(challenge_id) + "-" + username,
            "labels": {
                "ctf-id-username": "ctf-" + str(challenge_id) + "-" + username,
                "username": username,
                "name": name,
                "challenge_id": challenge_id,
                "mode": mode},
            "namespace": "project",
        },
        "spec": {
            "parentRefs": [{"name": "project-gateway"}],
            "rules": [
                {
                    "matches": [
                        {
                            "path": {
                                "type": "PathPrefix",
                                "value": "/ctf/" + str(challenge_id) + "-" + username,
                            }
                        }
                    ],
                    "backendRefs": [
                        {"name": "svc-" + str(challenge_id) +
                         "-" + username, "port": 80}
                    ],
                    "filters": [
                        {
                            "type": "URLRewrite",
                            "urlRewrite": {
                                "path": {
                                    "replacePrefixMatch": "/",
                                    "type": "ReplacePrefixMatch",
                                }
                            },
                        }
                    ],
                }
            ],
        },
    }
    return route_dict

def get_active_instances(claims):
    """Returns all active instances"""
    load_kubernetes_config()
    v1 = client.CoreV1Api()
    if claims["role"] == "admin":
        active_challenges = v1.list_namespaced_pod(namespace='project', label_selector=f'type=ctf').items
    else:
        active_challenges = v1.list_namespaced_pod(namespace='project', label_selector=f'type=ctf,username={claims["sub"]}').items

    active_challenges_labels = [challenge.metadata.labels for challenge in active_challenges]
    return active_challenges_labels