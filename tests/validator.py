import unittest
import requests
import os


class ValidatorServerTestCase(unittest.TestCase):
    """
    This class contains integration tests for the Validator server.
    """

    def setUp(self):
        self.base_url = os.getenv("VALIDATOR_BASE_URL", "http://localhost:8000")

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

    def get_recent_tweets(self):
        """
        Test that the server is running and can receive calls through /healthcheck endpoint.
        """
        healthcheck_url = f"{self.base_url}/data/twitter/tweets/recent"
        response = requests.get(healthcheck_url)

        if response.status_code == 200:
            tweets = response.json()
            if len(tweets) > 0:
                success = True
            else:
                success = False
        else:
            self.assertTrue(False, f"Response status code: {response.status_code}")

        self.assertTrue(success, "No tweets found in fetching recent tweets")

        self.assertEqual(
            response.status_code,
            200,
            "Server is not running or not reachable on /healthcheck endpoint",
        )

        return tweets

    def get_volumes(self):
        """
        Test that the server is running and can receive calls through /volumes endpoint.
        """
        volumes_url = f"{self.base_url}/volumes"
        response = requests.get(volumes_url)

        if response.status_code == 200:
            volumes = response.json()

            print(volumes)
            if len(volumes) > 0:
                success = True
            else:
                success = False
        else:
            self.assertTrue(False, f"Response status code: {response.status_code}")

        self.assertTrue(success, "No volumes found in fetching volumes")

        self.assertEqual(
            response.status_code,
            200,
            "Server is not running or not reachable on /volumes endpoint",
        )

        return volumes

    def test_volumes_change_after_getting_recent_tweets(self):
        """
        Test that volumes change after getting recent tweets if tweets are more than 0.
        """
        import time

        # Initial volume check
        initial_volumes = self.get_volumes()
        initial_latest_tempo = initial_volumes[-1]["tempo"]
        initial_miners = initial_volumes[-1]["miners"]
        print("Initial volumes:", initial_volumes)

        # Fetch recent tweets
        tweets = self.get_recent_tweets()
        tweets_length = len(tweets)
        print("Tweets length:", tweets_length)

        # Wait for 2 seconds before checking volumes again
        time.sleep(15)

        # Volume check after fetching tweets
        final_volumes = self.get_volumes()
        final_latest_tempo = final_volumes[-1]["tempo"]
        final_miners = final_volumes[-1]["miners"]
        print("Final volumes:", final_volumes)

        # Check if the latest tempo is the same
        self.assertEqual(
            initial_latest_tempo,
            final_latest_tempo,
            "Latest tempo did not remain the same after fetching recent tweets",
        )

        # Check if any of the fields in miners changed
        self.assertNotEqual(
            initial_miners,
            final_miners,
            "Miners' fields did not change after fetching recent tweets",
        )


if __name__ == "__main__":
    unittest.main()
