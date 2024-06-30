"""Functions to fetch data from INE's API"""

import pandas as pd
import requests

from .models import Response, Indicator

INE_API_BASE_URL = "https://www.ine.pt/ine/json_indicador"

def quarter_to_date(quarter_string):
    # Splitting the string to extract quarter and year
    parts = quarter_string.split()
    quarter = parts[0]
    year = parts[2]

    # Mapping the quarter to a month
    quarter_month_map = {
        "1st": "03",
        "2nd": "06",
        "3rd": "09",
        "4th": "12"
    }
    month = quarter_month_map.get(quarter, "01")  # Default to January if not found

    # Forming a new date string (assuming last day of the month)
    date_str = pd.to_datetime(f"{year}-{month}", format="%Y-%m")

    # Converting to datetime
    return date_str


def request(
    indicator_code: str,
    data_type: str,
    dim_values: dict = None
) -> Response:
    """Fetch data for an indicator from INE's API.

    Keyword arguments:
    indicator_code -- The indicator code to fetch the data for (e.g. "0006341")
    data_type -- What to request. Can be "data" or "metadata"

    Returns:
    The requests.Response object for the request sent to INE's API TODO: It's not the requests.Response object, but our own Response object

    Raises:
    ValueError: If the 'request' parameter is not 'data' or 'metadata'.
    """

    if data_type == "data":
        dim_values_str = "Dim1=T"
        if dim_values is not None:
            if "Dim1" not in dim_values:
                dim_values["Dim1"] = "T"

            dim_values_str = "&".join(
                [f"{key}={value}" for key, value in dim_values.items()]
            )

        res = requests.get(
            f"{INE_API_BASE_URL}/pindica.jsp?op=2&varcd={indicator_code}&lang=EN&{dim_values_str}",
            timeout=20,
        )

        return Response(res)

    if data_type == "metadata":
        res = requests.get(
            f"{INE_API_BASE_URL}/pindicaMeta.jsp?varcd={indicator_code}&lang=EN",
            timeout=20,
        )

        return Response(res)

    raise ValueError(
        f"Invalid data type: '{data_type}'. Expected 'data' or 'metadata'."
    )


def get_indicator(
    indicator_code: str = None,
    dim_values: dict = None,
    data: str = None,
    metadata: str = None
) -> pd.DataFrame:
    """
    Fetch the data for an indicator from INE's API and return it as a pandas DataFrame

    Keyword arguments:
    indicator_code -- The indicator code to fetch the data for (e.g. "0006341")
    data -- The indicator's raw JSON data from INE. If None, it will be fetched from INE's API
    metadata -- The indicator's metadata from INE. If None, it will be fetched from INE's API
    """

    if indicator_code is None and (data is None or metadata is None):
        raise ValueError(
            "Either the indicator_code parameter or both the data and metadata parameters must be set"
        )

    dim_values = {str(key): value for key, value in dim_values.items()} if dim_values is not None else {}

    if data is None:
        data_res = request(indicator_code, "data", dim_values)
        data_res.raise_for_status()
        data = data_res.json()

    if metadata is None:
        meta_res = request(indicator_code, "metadata")
        meta_res.raise_for_status()
        metadata = meta_res.json()

    data = data[0]
    metadata = metadata[0]

    # Process the data into a pandas DataFrame.
    col_index_iterables = []
    col_index_names = []

    for dim_description in metadata["Dimensoes"]["Descricao_Dim"]:
        dim_num = dim_description["dim_num"]

        if dim_num == "1":
            continue

        dim_columns = []

        for key, value in metadata["Dimensoes"]["Categoria_Dim"][0].items():
            if key.startswith(f"Dim_Num{dim_num}"):
                if f"Dim{dim_num}" in dim_values:
                    dim_value = dim_values[f"Dim{dim_num}"]
                    if key.endswith(f"_{dim_value}"):
                        dim_columns.append(value[0]["categ_dsg"])
                else:
                    dim_columns.append(value[0]["categ_dsg"])

        col_index_iterables.append(dim_columns)
        col_index_names.append(dim_description["abrv"])

    col_index = pd.MultiIndex.from_product(col_index_iterables)
    col_index.names = ["Location"] + col_index_names[1:]

    df = pd.DataFrame(index=data["Dados"].keys(), columns=col_index)

    df.sort_index(axis=1, inplace=True)

    for date, period_stats in data["Dados"].items():
        for stat in period_stats:
            dim_values = (stat['geocod'],) + tuple(stat[f"dim_{i}_t"] for i in range(3, len(metadata["Dimensoes"]["Descricao_Dim"]) + 1))

            if "valor" in stat:
                df.loc[date, dim_values] = stat["valor"]

    if metadata["Periodic"] in ["Annual", "Decennial"]:
        df.index = pd.to_datetime(df.index, format="%Y")
    elif metadata["Periodic"] == "Quarterly":
        df.index = df.index.map(quarter_to_date)
    elif metadata["Periodic"] == "Monthly":
        df.index = pd.to_datetime(df.index, format="%B %Y")

    df.index.names = ["Period"]

    # Merge the metadata from the indicator's data and metadata responses into a single dict.
    metadata_key_map = {
        "IndicadorCod": "code",
        "IndicadorDsg": "description",
        "MetaInfUrl": "meta_info_url",
        "DataUltimoAtualizacao": "last_update_date",
        "Periodic": "periodicity",
        "PrimeiroPeriodo": "first_period",
        "UltimoPref": "last_period",
        "UltimoPeriodo": "last_period",
        "UnidadeMedida": "unit",
        "Potencia10": "power_of_10",
        "PrecisaoDecimal": "decimal_precision",
        "Lingua": "language",
    }

    merged_metadata = {
        "extraction_date": {
            "data": data["DataExtracao"],
            "metadata": metadata["DataExtracao"],
        },
        "source": "INE",
    }

    for key, value in {**data, **metadata}.items():
        if key in ["Dados", "DataExtracao", "Dimensoes", "Sucesso"]:
            continue

        if key in ["PrimeiroPeriodo", "UltimoPeriodo"]:
            if metadata["Periodic"] in ["Annual", "Decennial"]:
                value = pd.to_datetime(value, format="%Y")
            elif metadata["Periodic"] == "Quarterly":
                value = quarter_to_date(value)
            elif metadata["Periodic"] == "Monthly":
                value = pd.to_datetime(value, format="%B %Y")

            value = value.strftime('%Y-%m-%d')

        merged_metadata[metadata_key_map.get(key, key)] = value

    if "(NUTS - 2013)" in merged_metadata["description"]: # TODO: add support for other geo standards
        merged_metadata["geo_level"] = "nuts-2013"
    elif "(NUTS - 2002)" in merged_metadata["description"]:
        merged_metadata["geo_level"] = "nuts-2002"
    else:
        merged_metadata["geo_level"] = "national"

    return Indicator(df, merged_metadata)
