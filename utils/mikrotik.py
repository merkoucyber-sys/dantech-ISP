import routeros_api

from netcore.settings import MIKROTIK


def get_api():
    connection = routeros_api.RouterOsApiPool(
        host=MIKROTIK["HOST"],
        username=MIKROTIK["USERNAME"],
        password=MIKROTIK["PASSWORD"],
        port=MIKROTIK["PORT"],
        plaintext_login=True,
    )
    return connection.get_api()