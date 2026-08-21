import re
import pandas as pd


def normalize_year(value):
    """
    Convert different year formats into a consistent year value.

    Examples:
        Dec 2012 -> 2012
        Mar 2014 -> 2014
        Mar-15   -> 2015
        2024     -> 2024
    """
    if pd.isna(value):
        return None

    value = str(value).strip()

    # Find a four-digit year
    match = re.search(r"(19|20)\d{2}", value)
    if match:
        return int(match.group())

    # Find two-digit year such as Mar-15
    match = re.search(r"-(\d{2})$", value)
    if match:
        year = int(match.group(1))

        if year >= 50:
            return 1900 + year
        else:
            return 2000 + year

    return None


def normalize_ticker(value):
    """
    Standardize company ticker/company ID.

    Examples:
        ' ABB '       -> 'ABB'
        'abb'         -> 'ABB'
        'HDFCBANK '   -> 'HDFCBANK'
    """
    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    # Remove unwanted spaces
    value = re.sub(r"\s+", "", value)

    return value