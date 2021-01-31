import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from lambda_handler import LambdaHandler
from .. import GeocodePropertyLambdaCore, ApiMetadata
from ..mongo import MongoDBConnection, MONGODB_CONNECTION


API_GEOCODING_METADATA = ApiMetadata(
    base_url='https://api.mapbox.com/geocoding/v5/mapbox.places/',
    access_token=os.getenv('API_ACCESS_TOKEN_GEOCODING')
)


@dataclass(init=False)
class GeocodePropertyLambda(LambdaHandler):

    logger: logging.Logger
    mongodb_connection: MongoDBConnection

    def __init__(self, logger, mongodb_connection):

        super().__init__(logger=logger)
        self.mongodb_connection = mongodb_connection
        self.core = GeocodePropertyLambdaCore(
            logger=self.logger,
            mongodb_connection=mongodb_connection,
            api_geocoding=API_GEOCODING_METADATA
        )

    def run(self, event: Any, context: Any) -> Any:

        message = event['Records'][0]['Sns']['Message']
        property = json.loads(message)
        property_geocoded = self.core.geocode_property(property=property)
        property_geohashed = self.core.geohash_property(property=property_geocoded)
        self.core.archive_property(property=property_geohashed)


LAMBDA_HANDLER = GeocodePropertyLambda(
    logger=logging.getLogger(),
    mongodb_connection=MONGODB_CONNECTION
)
