"""
PyINE Library
~~~~~~~~~~~~~

PyINE is a Python library for interacting with the Portuguese Instituto
Nacional de Estatística (INE)'s API.

:copyright: (c) 2024 by Gonçalo Figueiredo.
:license: Apache 2.0, see LICENSE for more details.
"""

__version__ = "0.1.0"

from .api import get_indicator, request
from .exceptions import INEInvalidRequestError
from .models import Indicator, Response
