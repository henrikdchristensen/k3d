import requests

def test_comm1():
    # Use the Kubernetes DNS name for the user service
    response = requests.get('http://service-user')
    assert response.status_code == 200

def test_comm2():
    # Use the Kubernetes DNS name for the user service
    response = requests.get('http://service-user:8082')
    assert response.status_code == 200

def test_comm3():
    # Use the Kubernetes DNS name for the user service
    response = requests.get('localhost/user') # Access from another service: http://service-user.project.svc.cluster.local
    assert response.status_code == 200
