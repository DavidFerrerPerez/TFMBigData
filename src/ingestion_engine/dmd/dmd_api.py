import requests
import json
from requests.adapters import HTTPAdapter

class DMDApi:

    REQUEST_TIMEOUT = (5, 30)

    def __init__(self, dmd_api_url: str, token: str = None):

        self.dmd_api_url = dmd_api_url
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
        }
        self._templates = None
        self._maindata = None
        self._maindata_by_code = None
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


    def post_response(self, url, body, headers, params=None):
        """
        Sends a POST request to the specified URL with the given body, headers, and optional parameters.

        Args:
            url (str): The URL to send the POST request to.
            body (dict or str): The body of the POST request.
            headers (dict): The headers to include in the POST request.
            params (dict, optional): The query parameters to include in the POST request. Defaults to None.

        Returns:
            requests.Response: The response object from the POST request.
        """
        return self._session.post(url, verify=True, params=params, headers=headers, data=body, timeout=self.REQUEST_TIMEOUT)


    def _get_templates(self):
        """
        Fetches the list of templates from the DMD API.

        Returns:
            list: A list of templates retrieved from the DMD API.
        """

        if self._templates is None:

            response = self.get_response(
                self.dmd_api_url + "/api/v2/template/", headers=self.headers)

            response.raise_for_status()

            self._templates = response.json()

        return self._templates

    def get_template_metadata(self, code: str) -> dict:
        """
        Fetches the metadata for a given template code from the DMD API.

        Args:
            code (str): The code of the template.

        Returns:
            dict: The metadata of the template retrieved from the DMD API.
        """

        templates = self._get_templates()
                
        for template in templates:
            if template.get("code") == code:

                template_metadata = {
                    "id": template.get("id"),
                    "code": template.get("code"),
                    "name": template.get("name"),
                    "is_deleted": template.get("isDeleted"),
                    "is_enabled": template.get("isEnabled"),
                    "geometry_type": template.get("geometryType")
                }
                return template_metadata

        raise ValueError(f"Template with code '{code}' not found in the response.")


    def get_template_schema_by_id(self, template_id: int) -> list:

        """
        Fetches the schema for a given template ID from the DMD API.

        Args:
            template_id (int): The ID of the template.

        Returns:
            list: A list of characteristics of the template retrieved from the DMD API.
        """

        response = self.get_response(
            f"{self.dmd_api_url}/api/v2/template/description/{template_id}",
            headers=self.headers,
        )
        response.raise_for_status()
        return response.json().get("characteristics", [])


    def _get_maindata_values(self):
        """
        Fetches the maindata values for a given maindata relation master from the DMD API.

        Returns:
            list: A list of maindata values retrieved from the DMD API.
        """
        if self._maindata is None:
            response = self.get_response(f'{self.dmd_api_url}/api/v2/masterdata/by-parameters/?relationMasterIdFrom=1&relationMasterIdTo=99999', headers=self.headers)
            response.raise_for_status()
            self._maindata = response.json()

        return self._maindata

    def get_maindata_values_by_code(self, maindata_relation_master: str) -> dict:
        """
        Get the maindata value-to-ID mapping for a given relation master.

        Args:
            maindata_relation_master (str): Code or name of the maindata relation master.

        Returns:
            dict: Dictionary mapping maindata names to their IDs.
        """
        if self._maindata_by_code is None:
            maindata_list = self._get_maindata_values()

            self._maindata_by_code = {}

            for maindata in maindata_list:
                values = {
                    maindata_value.get("name"): maindata_value.get("id")
                    for maindata_value in maindata.get("relations", [])
                }

                if maindata.get("code"):
                    self._maindata_by_code[maindata.get("code")] = values

                if maindata.get("name"):
                    self._maindata_by_code[maindata.get("name")] = values

        return self._maindata_by_code.get(maindata_relation_master, {})

    def create_assets(self, assets: list):
        """
        This method is used to create new assets in the DMD service.
        It makes a POST request to the '/api/v2/assets/' endpoint of the DMD service.

        Args:
            assets (list): A list of Asset objects to be created.

        Returns:
            Response: The response from the POST request, which includes the created assets.
        """

        response = self.post_response(
            url=f"{self.dmd_api_url}/api/v2/assets/",
            body=json.dumps(assets),
            headers=self.headers
        )

        return response