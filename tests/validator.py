import unittest
import requests


class ValidatorServerTestCase(unittest.TestCase):
    """
    This class contains integration tests for the Validator server.
    """

    def setUp(self):
        self.base_url = "http://localhost:8000"

    def test_server_running(self):
        """
        Test that the server is running and can receive calls through /healthcheck endpoint.
        """
        healthcheck_url = f"{self.base_url}/healthcheck"
        response = requests.get(healthcheck_url)
        self.assertEqual(
            response.status_code,
            200,
            "Server is not running or not reachable on /healthcheck endpoint",
        )

    def test_validator_twitter_profile(self):
        """
        Test that the validator twitter endpoint is reachable and returns the expected response.
        """
        endpoint = f"{self.base_url}/data/twitter/profile/getmasafi"
        response = requests.get(endpoint)
        self.assertEqual(
            response.status_code,
            200,
            "Validator endpoint is not reachable or not returning 200 OK",
        )

        result = response.json()
        self.assertIsInstance(result, list, "Result is not an array")


if __name__ == "__main__":
    unittest.main()
