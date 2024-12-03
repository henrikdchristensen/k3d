import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_comm3():
    logger.info("Testing user endpoint at http://localhost/user")
    response = requests.get('http://localhost/user')
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response body: {response.text}")
    assert response.status_code == 200, "Expected status code 200"
