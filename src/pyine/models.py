"""
pyine.models
~~~~~~~~~~~~

This module contains the primary objects that power PyINE.
"""

import pandas as pd
import requests

from .exceptions import INEInvalidRequestError


class Response(requests.Response):
    """The :class:`Response <Response>` object, which contains INE's response to an HTTP request.

    This class is a subclass of :class:`requests.Response <requests.Response>`, and as such
    exposes all of the same attributes and methods as that class.
    """

    def __init__(
        self, response: requests.Response
    ):  # pylint: disable=W0231:super-init-not-called
        self.__dict__ = response.__dict__

    def raise_for_status(self):
        """Raises :class:`HTTPError` or :class:`INEInvalidRequestError`, if one occurred."""

        super().raise_for_status()

        if self.is_ine_error():
            raise INEInvalidRequestError(self)

    def is_ine_error(self) -> bool:
        """Check if INE returned an error for an invalid, but successful, request.

        Does not check if the request itself failed. It assumes that the request was successful
        (i.e. response.status_code == 200).

        Keyword arguments:
        response -- The response to check

        Returns:
        True if the response failed, False otherwise
        """
        response_data = self.json()

        return (
            isinstance(response_data, list)
            and response_data
            and "Sucesso" in response_data[0]
            and "Falso" in response_data[0]["Sucesso"]
        )


class Indicator:
    """
    The :class:`Indicator <Indicator>` object, which contains an indicator data and metadata.

    Attributes:
    data -- The indicator's data as a pandas DataFrame
    metadata -- The indicator's metadata as a dict
    code -- The indicator's code
    description -- The indicator's description
    meta_info_url -- The URL to the indicator's metadata page on INE's website
    extraction_date -- A dict with the date the indicator's data and metadata was extracted from INE's API
    last_update_date -- The date the indicator was last updated
    periodicity -- The periodicity of the indicator's data (e.g. "Monthly")
    first_period -- The first period the indicator has data for
    last_period -- The last period the indicator has data for
    unit -- The unit in which the indicator's data is measured
    power_of_10 -- The power of 10 the indicator's data is multiplied by
    decimal_precision -- The number of decimal places the indicator's data is rounded to
    language -- The indicator's language (e.g. "EN")
    """

    def __init__(self, data: pd.DataFrame, metadata: dict):
        self.data = data
        self.metadata = metadata

    def __getattr__(self, name):
        """
        Get an attribute from the indicator's metadata.

        Keyword arguments:
        name -- The name of the attribute to get
        """
        if name in self.metadata:
            return self.metadata[name]

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}' and '{name}' is not a valid metadata attribute"
        )

    def __repr__(self):
        """
        Return a string representation of the indicator.
        """
        return f"<Indicator: {self.description} ({self.code})>"

    def to_dict(self):
        """
        Convert the Indicator instance to a dictionary including all its properties.
        """
        result = {key: value for key, value in self.metadata.items()}

        df = self.data.reset_index()

        df_melted = df.melt(
            id_vars=[df.columns[0]],
            value_name="Value",
        )

        df_melted.columns.values[0] = self.data.index.name

        df_melted["Value"] = pd.to_numeric(df_melted["Value"], errors="coerce")

        df_melted['Period'] = df_melted['Period'].dt.strftime('%Y-%m-%d')

        result['data'] = df_melted.to_dict(orient="records")

        return result
