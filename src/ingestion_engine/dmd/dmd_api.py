import requests

class DMDApi:

    def __init__(self, dmd_api_url: str, token: str = None):

        self.dmd_api_url = dmd_api_url
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
        }
        self._templates = None
        self._maindata = None

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
        return requests.get(url, verify=False, headers=headers, params=params)


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
        return requests.post(url, verify=False, params=params, headers=headers, data=body)


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
                return template

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
            self.dmd_api_url + f"/api/v2/template/description/{template_id}", headers=self.headers)

        if response.status_code == 200:
            return response.json().get("characteristics", [])
        return response


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

    def get_maindata_values_by_code(self, maindata_relation_master: str):
        """
        Fetches the maindata values for a given maindata relation master from the DMD API.

        Args:
            maindata_relation_master (str): The name of the maindata relation master.

        Returns:
            list: A list of maindata values retrieved from the DMD API.
        """
        

        maindata_list = self._get_maindata_values()
        for maindata in maindata_list:
            if maindata.get("code") == maindata_relation_master or maindata.get("name") == maindata_relation_master:
                return {maindata_value.get("name"): maindata_value.get("id") for maindata_value in maindata.get("relations")}
        return []