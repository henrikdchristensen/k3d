import requests

def test_comm():
    # Request user service via http
    response = requests.get('http://localhost/user')
    assert response.status_code == 200