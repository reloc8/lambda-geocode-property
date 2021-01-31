import bson
import json
import logging
import pygeohash
import pymongo
import urllib3
from dataclasses import dataclass
from typing import Any, AnyStr, Dict

from .mongo import MongoDBConnection, MONGODB_CONNECTION


MONGODB_CLIENT = pymongo.MongoClient(MONGODB_CONNECTION.uri)

POOL_MANGER = urllib3.PoolManager(
    num_pools=10,
    retries=0,
    timeout=urllib3.Timeout(connect=2, read=5)
)


@dataclass
class ApiMetadata:

    base_url: AnyStr
    access_token: AnyStr


@dataclass
class GeocodePropertyLambdaCore:

    logger: logging.Logger
    mongodb_connection: MongoDBConnection
    api_geocoding: ApiMetadata

    def geocode_property(self, property: Dict[AnyStr, Any]) -> Dict[AnyStr, Any]:

        id_ = property['id']
        address = property['location']['address']
        city = property['location']['city']

        latitude, longitude = None, None
        if address and city:

            query = f'{address}, {city}'

            url = f'{self.api_geocoding.base_url}{query}.json'
            params = dict(access_token=self.api_geocoding.access_token, types='address')
            response = POOL_MANGER.request(method='GET', url=url, headers={}, fields=params)
            status_code = response.status
            if status_code == 200:
                data = json.loads(response.data)
                best_result = data['features'][0]
                latitude = best_result['center'][1]
                longitude = best_result['center'][0]
            else:
                self.logger.error(f'Received response with unexpected status: {status_code}')
        else:
            self.logger.warning(f'Missing geolocation information for property with id "{id_}".')

        location = {
            'point': {
                'type': 'Point',
                'coordinates': [
                    longitude,
                    latitude
                ]
            }
        }
        property['location'] = location

        return property

    def geohash_property(self, property: Dict[AnyStr, Any]) -> Dict[AnyStr, Any]:

        _id = property['id']
        location = property['location']
        coordinates = location['point']['coordinates']
        latitude = coordinates[1]
        longitude = coordinates[0]

        geohash = None
        if latitude and longitude:
            geohash = pygeohash.encode(latitude=latitude, longitude=longitude, precision=9)
        else:
            self.logger.warning(f'Missing geocoding information for property with id "{_id}".')

        location['geohash'] = geohash

        return property

    def archive_property(self, property: Dict[AnyStr, Any]) -> None:

        property['_id'] = property['id']
        del property['id']
        property['cursor'] = bson.ObjectId()

        database = self.mongodb_connection.database
        collection = self.mongodb_connection.collection
        MONGODB_CLIENT[database][collection].insert_one(property)
