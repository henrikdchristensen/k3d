import requests

def test_comp_communication():
    response = requests.get('http://localhost/comp')
    assert response.status_code == 200, "Expected status code 200"

def test_ctf_communication():
    response = requests.get('http://localhost/ctf')
    assert response.status_code == 200, "Expected status code 200"

def test_user_communication():
    response = requests.get('http://localhost/user')
    assert response.status_code == 200, "Expected status code 200"
