import requests
from requests.adapters import HTTPAdapter

class IOTCoreAPI:

    REQUEST_TIMEOUT = (5, 30)

    def __init__(self, iotcore_api_url: str, token: str = None, driver: str = None):

        self.iotcore_api_url = iotcore_api_url
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
        }
        self.driver = driver
        self._tags = None
        self._tags_by_name = None
        self._session = requests.Session()
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def get_response(self, url, headers, params=None):
        """
        Sends a GET request to the specified URL with the given headers and optional parameters.

        Args:
            url (str): The URL to send the GET request to.
            headers (dict): The headers to include in the GET request.
            params (dict, optional): The query parameters to include in the GET request. Defaults to None.

        Returns:
            requests.Response: The response object from the GET request.
        """
        return self._session.get(url, verify=True, headers=headers, params=params, timeout=self.REQUEST_TIMEOUT)

    def _catalogue_tags(self):
        """
        Fetches the catalogue tags from the IOTCore API.

        Returns:
            list: A list of catalogue tags retrieved from the IOTCore API.
        """
        if self._tags is None:
            response = self.get_response(f'{self.iotcore_api_url}/api/v1/catalogue/tags', headers=self.headers, params={"Driver": self.driver})
            response.raise_for_status()
            self._tags = response.json()

        return self._tags

    
    def _catalogue_tags_by_name(self) -> dict[str, list[str]]:
        if self._tags_by_name is None:
            self._tags_by_name = {}

            for tag in self._catalogue_tags():
                name = tag.get("name")
                uid = tag.get("uid")
                if name and uid:
                    self._tags_by_name.setdefault(name, []).append(uid)

        return self._tags_by_name

    def get_uids_from_tag_name(self, tag_name: str):
        """
        Fetches the UID of a tag from the IOTCore API based on the tag name.

        Args:
            tag_name (str): The name of the tag to fetch the UID for.

        Returns:
            list[str]: A list of UIDs associated with the given tag name.
        """
        return self._catalogue_tags_by_name().get(tag_name, [])
    