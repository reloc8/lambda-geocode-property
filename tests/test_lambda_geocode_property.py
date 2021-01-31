import json
import os
import pymongo
import unittest
import unittest.mock as mock

from dataclasses import dataclass
from testcontainers.mongodb import MongoDbContainer
from typing import AnyStr


@dataclass
class MockUrllibResponse:

    data: AnyStr
    status: int


class TestGeocodePropertyLambda(unittest.TestCase):

    @mock.patch('urllib3.PoolManager.request')
    def testRunWhenReceiveSnsEvent(self, mock_urllib_response):

        with MongoDbContainer('mongo:latest') as mongodb:

            mongodb_uri = mongodb.get_connection_url()
            os.environ['MONGODB_URI'] = mongodb_uri
            os.environ['API_ACCESS_TOKEN_GEOCODING'] = 'dummy_token'

            with open('resources/properties-1.json', 'r') as file:
                properties = json.load(file)

            with open('resources/event-sns.json', 'r') as file:
                event = json.load(file)

            with open('resources/properties-geocoded-1.json', 'r') as file:
                properties_geocoded = json.load(file)

            with open('resources/api-response-mapbox.json', 'r') as file:
                api_geocoding_response = file.read()

            event['Records'][0]['Sns']['Message'] = json.dumps(properties[0])

            mock_urllib_response.return_value = MockUrllibResponse(data=api_geocoding_response, status=200)

            from geocode_property.core.handler import LAMBDA_HANDLER, MONGODB_CONNECTION

            LAMBDA_HANDLER.run(event=event, context=None)

            mongodb_connection = MONGODB_CONNECTION
            mongodb_database = mongodb_connection.database
            mongodb_collection = mongodb_connection.collection
            mock_mongodb_client = pymongo.MongoClient(mongodb_uri)
            results = list(mock_mongodb_client[mongodb_database][mongodb_collection].find())

            self.assertEqual(1, len(results))

            expected_result = properties_geocoded[0]
            expected_result['cursor'] = mock.ANY
            actual_result = results[0]

            self.assertIsNotNone(actual_result['cursor'])
            self.assertDictEqual(expected_result, actual_result)


if __name__ == '__main__':
    unittest.main()
