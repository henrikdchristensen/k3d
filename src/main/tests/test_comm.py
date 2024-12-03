import requests

def test_comm():
    # Use the Kubernetes DNS name for the user service
    response = requests.get('http://service-user.project.svc.cluster.local/user')
    assert response.status_code == 200