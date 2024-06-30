"""
pyine.exceptions
~~~~~~~~~~~~~~~~

This module contains our custom exceptions.
"""

import requests


class INEInvalidRequestError(Exception):
    """INE returned an error."""

    def __init__(
        self, response: requests.Response, message: str = "INE returned an error."
    ):
        self.response = response
        self.message = message
        self.ine_errors = self.get_ine_errors()

        super().__init__()

    def __str__(self):
        if "Msg" in self.ine_errors[0]:
            return f"{self.message} Error: {self.ine_errors[0]['Msg']}"

        return self.message

    def get_ine_errors(self) -> list:
        """
        Get all errors returned by INE on an invalid, but successful, request.

        Returns:
        A list of errors
        """
        response_data = self.response.json()

        if (
            isinstance(response_data, list)
            and response_data
            and "Sucesso" in response_data[0]
            and "Falso" in response_data[0]["Sucesso"]
            and isinstance(response_data[0]["Sucesso"]["Falso"], list)
            and response_data[0]["Sucesso"]["Falso"]
        ):
            return response_data[0]["Sucesso"]["Falso"]

        return []
