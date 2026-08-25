import requests

class DMDApi:

    def __init__(self, dmd_api_url: str, token: str = None):

        self.dmd_api_url = dmd_api_url
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
        }

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

    def get_template_id_by_code(self, code: str):

        response = self.get_response(
            self.dmd_api_url + f"/api/v2/template/?code={code}", headers=self.headers)

        if response.status_code == 200:
            templates = response.json()
            for template in templates:
                if template.get("code") == code:
                    return template.get("id")

            raise ValueError(f"Template with code '{code}' not found in the response.")
        return response


    def get_template_schema_by_id(self, template_id: int):

        response = self.get_response(
            self.dmd_api_url + f"/api/v2/template/description/{template_id}", headers=self.headers)

        if response.status_code == 200:
            return response.json().get("characteristics", [])
        return response