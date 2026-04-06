"""
Data fetcher module for SCB (Statistics Sweden) PxWeb API.

This module provides classes for fetching municipal financial data from SCB's
statistical database using their PxWeb JSON-stat API.

All variable names, comments, and docstrings in English.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

from src.config import (
    SCB_API_BASE,
    SCB_API_URLS,
    KOLADA_API_BASE,
    KOLADA_UNEMPLOYMENT_KPIS,
    YEARS,
    YEARS_STR,
    POPULATION_YEARS_STR,
    START_YEAR,
    END_YEAR,
    CACHE_DIR,
    RAW_DIR,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    CACHE_EXPIRY_DAYS,
    BALANCE_SHEET_POSTS,
    MUNICIPALITIES,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SCBAPIError(Exception):
    """Custom exception for SCB API errors."""
    pass


class KoladaAPIError(Exception):
    """Custom exception for Kolada API errors."""
    pass


class SCBFetcher:
    """
    Client for fetching data from SCB's PxWeb API.

    Handles POST requests with JSON query bodies, response parsing,
    caching, and retry logic with exponential backoff.

    Attributes:
        cache_dir: Directory for caching fetched data
        raw_dir: Directory for saving raw API responses
    """

    def __init__(
        self,
        cache_dir: str = CACHE_DIR,
        raw_dir: str = RAW_DIR,
        use_cache: bool = True
    ):
        """
        Initialize the SCB API fetcher.

        Args:
            cache_dir: Directory path for cache files
            raw_dir: Directory path for raw data files
            use_cache: Whether to use cached data if available
        """
        self.cache_dir = Path(cache_dir)
        self.raw_dir = Path(raw_dir)
        self.use_cache = use_cache

        # Create directories if they don't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def _build_query(
        self,
        variables: List[Dict[str, Any]],
        years: List[str],
        region_filter: str = "vs:RegionKommun07"
    ) -> Dict[str, Any]:
        """
        Build a PxWeb API query body.

        Args:
            variables: List of variable selections (code, filter, values)
            years: List of years to fetch
            region_filter: Filter for municipality selection

        Returns:
            Query body dictionary for POST request
        """
        query = {
            "query": [
                {
                    "code": "Region",
                    "selection": {
                        "filter": region_filter,
                        "values": []  # Empty = all municipalities
                    }
                },
                *variables,
                {
                    "code": "Tid",
                    "selection": {
                        "filter": "item",
                        "values": years
                    }
                }
            ],
            "response": {
                "format": "json"
            }
        }
        return query

    def _make_request(
        self,
        url: str,
        query: Dict[str, Any],
        table_name: str
    ) -> Dict[str, Any]:
        """
        Make a POST request to the SCB API with retry logic.

        Args:
            url: API endpoint URL
            query: Query body dictionary
            table_name: Name of the table for logging

        Returns:
            JSON response data

        Raises:
            SCBAPIError: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Fetching {table_name} from SCB API (attempt {attempt + 1}/{MAX_RETRIES})")
                logger.debug(f"URL: {url}")
                logger.debug(f"Query: {json.dumps(query, indent=2)}")

                response = self.session.post(
                    url,
                    json=query,
                    timeout=REQUEST_TIMEOUT
                )

                if response.status_code == 200:
                    logger.info(f"Successfully fetched {table_name}")
                    return response.json()
                elif response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = RETRY_BACKOFF_FACTOR ** (attempt + 2)
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    raise SCBAPIError(f"API returned status {response.status_code}: {response.text}")

            except requests.exceptions.Timeout:
                last_exception = SCBAPIError(f"Request timeout after {REQUEST_TIMEOUT}s")
                logger.warning(f"Timeout on attempt {attempt + 1}")
            except requests.exceptions.RequestException as e:
                last_exception = SCBAPIError(f"Request failed: {str(e)}")
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")

            # Exponential backoff before retry
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF_FACTOR ** attempt
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        raise last_exception or SCBAPIError(f"Failed to fetch {table_name} after {MAX_RETRIES} attempts")

    def _parse_json_stat(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        Parse SCB API response into a DataFrame.

        SCB API can return two different formats:
        1. JSON-stat format with dimension/value/id/size
        2. Table format with columns/data structure

        Args:
            data: API response data

        Returns:
            DataFrame with parsed data
        """
        # Check which format we received
        if "data" in data and "columns" in data:
            # Table format (newer SCB API response)
            return self._parse_table_format(data)
        elif "dimension" in data and "value" in data:
            # JSON-stat format
            return self._parse_json_stat_format(data)
        else:
            logger.warning(f"Unknown API response format. Keys: {data.keys()}")
            return pd.DataFrame()

    def _parse_table_format(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        Parse SCB table format response.

        Format:
        {
            "columns": [{"code": "Region", "text": "region", "type": "d"}, ...],
            "data": [{"key": ["0180", "089", "2020"], "values": ["55382056"]}, ...]
        }
        """
        columns = data.get("columns", [])
        rows = data.get("data", [])

        if not columns or not rows:
            return pd.DataFrame()

        # Get column names (dimension columns + value columns)
        dim_cols = [c["code"] for c in columns if c.get("type") in ("d", "t")]
        val_cols = [c["code"] for c in columns if c.get("type") == "c"]

        # Build rows
        parsed_rows = []
        for row in rows:
            key = row.get("key", [])
            values = row.get("values", [])

            row_dict = {}
            # Add dimension values
            for i, col in enumerate(dim_cols):
                if i < len(key):
                    row_dict[col] = key[i]

            # Add value columns
            for i, col in enumerate(val_cols):
                if i < len(values):
                    row_dict[col] = values[i]

            parsed_rows.append(row_dict)

        df = pd.DataFrame(parsed_rows)

        # If we have a single value column, rename it to "value"
        if len(val_cols) == 1 and val_cols[0] in df.columns:
            df = df.rename(columns={val_cols[0]: "value"})

        return df

    def _parse_json_stat_format(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        Parse JSON-stat format response into a DataFrame.

        SCB's JSON-stat format has:
        - dimension: dict with dimension metadata
        - value: flat array of values
        - id: list of dimension names
        - size: list of dimension sizes

        Args:
            data: JSON-stat response data

        Returns:
            DataFrame with parsed data
        """
        # Extract dimension metadata
        dimensions = data.get("dimension", {})
        dim_ids = data.get("id", [])
        dim_sizes = data.get("size", [])
        values = data.get("value", [])

        # Build index arrays for each dimension
        dim_labels = {}
        for dim_id in dim_ids:
            dim_info = dimensions.get(dim_id, {})
            category = dim_info.get("category", {})
            index = category.get("index", {})
            label = category.get("label", {})

            # Sort by index position and get labels
            sorted_keys = sorted(index.keys(), key=lambda k: index[k])
            dim_labels[dim_id] = [label.get(k, k) for k in sorted_keys]

        # Create multi-index from all dimension combinations
        import itertools

        all_combinations = list(itertools.product(*[dim_labels[d] for d in dim_ids]))

        # Create DataFrame
        df = pd.DataFrame(all_combinations, columns=dim_ids)
        df["value"] = values

        return df

    def _get_cache_path(self, table_name: str) -> Path:
        """Get the cache file path for a table."""
        return self.cache_dir / f"{table_name}.parquet"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is not expired."""
        if not cache_path.exists():
            return False

        # Check file age
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age_days = (datetime.now() - file_time).days

        return age_days < CACHE_EXPIRY_DAYS

    def _save_to_cache(self, df: pd.DataFrame, table_name: str) -> None:
        """Save DataFrame to cache as parquet file."""
        cache_path = self._get_cache_path(table_name)
        df.to_parquet(cache_path, index=False)
        logger.info(f"Saved {table_name} to cache: {cache_path}")

    def _load_from_cache(self, table_name: str) -> Optional[pd.DataFrame]:
        """Load DataFrame from cache if valid."""
        cache_path = self._get_cache_path(table_name)

        if self.use_cache and self._is_cache_valid(cache_path):
            logger.info(f"Loading {table_name} from cache: {cache_path}")
            return pd.read_parquet(cache_path)

        return None

    def _save_raw_response(self, data: Dict[str, Any], table_name: str) -> None:
        """Save raw API response for debugging/reproducibility."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_path = self.raw_dir / f"{table_name}_{timestamp}.json"

        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"Saved raw response to: {raw_path}")

    def fetch_balance_sheet(self) -> pd.DataFrame:
        """
        Fetch balance sheet data (long-term liabilities) for all municipalities.

        Returns:
            DataFrame with columns: municipality_code, balanspost, year, value
            Value is in tkr (thousands of SEK)
        """
        table_name = "balance_sheet"

        # Check cache first
        cached = self._load_from_cache(table_name)
        if cached is not None:
            return cached

        url = SCB_API_URLS["balance_sheet"]

        # Balance sheet posts to fetch (codes from API)
        # 089 = LÅNGFRISTIGA SKULDER (Long-term debt)
        # 100 = SKULDER, AVSÄTTNINGAR OCH EGET KAPITAL (Total equity + liabilities)
        # 050 = SUMMA TILLGÅNGAR (Total assets)
        balance_post_codes = ["089", "100", "050"]

        # Build query for balance sheet data
        query = {
            "query": [
                {
                    "code": "Region",
                    "selection": {
                        "filter": "all",
                        "values": ["*"]  # All regions
                    }
                },
                {
                    "code": "Balansraknposter",
                    "selection": {
                        "filter": "item",
                        "values": balance_post_codes
                    }
                },
                {
                    "code": "ContentsCode",
                    "selection": {
                        "filter": "item",
                        "values": ["OE0107E5"]  # Tkr, löpande priser
                    }
                },
                {
                    "code": "Tid",
                    "selection": {
                        "filter": "item",
                        "values": YEARS_STR
                    }
                }
            ],
            "response": {"format": "json"}
        }

        # Make request
        data = self._make_request(url, query, table_name)
        self._save_raw_response(data, table_name)

        # Parse response
        df = self._parse_json_stat(data)

        if df.empty:
            logger.warning("Balance sheet query returned empty data")
            return df

        # Standardize column names
        df = df.rename(columns={
            "Region": "municipality_code",
            "Balansraknposter": "balanspost",
            "Tid": "year"
        })

        # Add municipality names from our mapping
        df["municipality_name"] = df["municipality_code"].map(MUNICIPALITIES)

        # Convert year to int
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

        # Convert value to numeric
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        # Save to cache
        self._save_to_cache(df, table_name)

        # Rate limiting delay
        time.sleep(REQUEST_DELAY)

        return df

    def fetch_population_by_age(self) -> pd.DataFrame:
        """
        Fetch population by age group for all municipalities.

        Fetches data from 2005 (needed for 5-year population growth calculation).

        Returns:
            DataFrame with columns: municipality_code, municipality_name, age, year, value
        """
        table_name = "population"

        # Check cache first
        cached = self._load_from_cache(table_name)
        if cached is not None:
            return cached

        url = SCB_API_URLS["population"]

        # Define age groups for our calculation
        # We need: 0-19 (young), 20-64 (working), 65+ (old)
        # SCB provides single ages (0, 1, 2, ..., 100+)
        # Let's fetch by 5-year groups to reduce data volume
        age_groups = [
            "0-4", "5-9", "10-14", "15-19",  # Young (0-19)
            "20-24", "25-29", "30-34", "35-39", "40-44",
            "45-49", "50-54", "55-59", "60-64",  # Working (20-64)
            "65-69", "70-74", "75-79", "80-84", "85-89", "90-94", "95-99", "100+"  # Old (65+)
        ]

        # Fetch total population plus key age groups for dependency ratio
        # Ages needed: 0-19 (young), 20-64 (working), 65+ (old), total
        # We'll fetch representative ages and aggregate

        # Select ages: all individuals to aggregate properly
        # This will return cross-tab that we aggregate in cleaner
        query = {
            "query": [
                {
                    "code": "Region",
                    "selection": {
                        "filter": "all",
                        "values": ["*"]  # All regions
                    }
                },
                {
                    "code": "Civilstand",
                    "selection": {
                        "filter": "all",
                        "values": ["*"]  # Will aggregate
                    }
                },
                {
                    "code": "Alder",
                    "selection": {
                        "filter": "item",
                        "values": ["tot"]  # Total population only for now
                    }
                },
                {
                    "code": "Kon",
                    "selection": {
                        "filter": "all",
                        "values": ["*"]  # Will aggregate
                    }
                },
                {
                    "code": "ContentsCode",
                    "selection": {
                        "filter": "item",
                        "values": ["BE0101N1"]  # Population count
                    }
                },
                {
                    "code": "Tid",
                    "selection": {
                        "filter": "item",
                        "values": POPULATION_YEARS_STR  # 2005-2024 for growth calc
                    }
                }
            ],
            "response": {"format": "json"}
        }

        # Make request
        data = self._make_request(url, query, table_name)
        self._save_raw_response(data, table_name)

        # Parse response
        df = self._parse_json_stat(data)

        if df.empty:
            logger.warning("Population query returned empty data")
            return df

        # Standardize column names
        col_mapping = {
            "Region": "municipality_code",
            "Civilstand": "marital_status",
            "Alder": "age",
            "Kon": "sex",
            "Tid": "year"
        }
        df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})

        # Add municipality names
        df["municipality_name"] = df["municipality_code"].map(MUNICIPALITIES)

        # Convert types
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        # Save to cache
        self._save_to_cache(df, table_name)

        time.sleep(REQUEST_DELAY)

        return df

    def fetch_tax_base(self) -> pd.DataFrame:
        """
        Fetch tax base strength (share of national average) for all municipalities.

        Returns:
            DataFrame with columns: municipality_code, municipality_name, year, value
            Value is percentage of national average (e.g., 100 = national average)
        """
        table_name = "tax_base"

        # Check cache first
        cached = self._load_from_cache(table_name)
        if cached is not None:
            return cached

        url = SCB_API_URLS["tax_base"]

        query = {
            "query": [
                {
                    "code": "Region",
                    "selection": {
                        "filter": "all",
                        "values": ["*"]
                    }
                },
                {
                    "code": "ContentsCode",
                    "selection": {
                        "filter": "item",
                        "values": ["OE0101B0"]  # Andel av riksmedelvärdet, procent
                    }
                },
                {
                    "code": "Tid",
                    "selection": {
                        "filter": "item",
                        "values": YEARS_STR
                    }
                }
            ],
            "response": {"format": "json"}
        }

        data = self._make_request(url, query, table_name)
        self._save_raw_response(data, table_name)

        df = self._parse_json_stat(data)

        if df.empty:
            logger.warning("Tax base query returned empty data")
            return df

        # Standardize column names
        df = df.rename(columns={
            "Region": "municipality_code",
            "Tid": "year"
        })

        df["municipality_name"] = df["municipality_code"].map(MUNICIPALITIES)

        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        self._save_to_cache(df, table_name)

        time.sleep(REQUEST_DELAY)

        return df

    def fetch_income_statement(self) -> pd.DataFrame:
        """
        Fetch income statement data (annual result) for all municipalities.

        Returns:
            DataFrame with columns: municipality_code, municipality_name, resultatpost, year, value
            Value is in tkr (thousands of SEK)
        """
        table_name = "income_statement"

        # Check cache first
        cached = self._load_from_cache(table_name)
        if cached is not None:
            return cached

        url = SCB_API_URLS["income_statement"]

        # 120 = Årets resultat (Annual result)
        query = {
            "query": [
                {
                    "code": "Region",
                    "selection": {
                        "filter": "all",
                        "values": ["*"]
                    }
                },
                {
                    "code": "Resultatraknposter",
                    "selection": {
                        "filter": "item",
                        "values": ["120"]  # Årets resultat
                    }
                },
                {
                    "code": "ContentsCode",
                    "selection": {
                        "filter": "item",
                        "values": ["OE0107E3"]  # Tkr, löpande priser
                    }
                },
                {
                    "code": "Tid",
                    "selection": {
                        "filter": "item",
                        "values": YEARS_STR
                    }
                }
            ],
            "response": {"format": "json"}
        }

        data = self._make_request(url, query, table_name)
        self._save_raw_response(data, table_name)

        df = self._parse_json_stat(data)

        if df.empty:
            logger.warning("Income statement query returned empty data")
            return df

        # Standardize column names
        df = df.rename(columns={
            "Region": "municipality_code",
            "Resultatraknposter": "resultatpost",
            "Tid": "year"
        })

        df["municipality_name"] = df["municipality_code"].map(MUNICIPALITIES)

        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        self._save_to_cache(df, table_name)

        time.sleep(REQUEST_DELAY)

        return df

    def fetch_tax_rate(self) -> pd.DataFrame:
        """
        Fetch municipal tax rate for all municipalities.

        Returns:
            DataFrame with columns: municipality_code, municipality_name, year, value
            Value is tax rate in percent
        """
        table_name = "tax_rate"

        # Check cache first
        cached = self._load_from_cache(table_name)
        if cached is not None:
            return cached

        url = SCB_API_URLS["tax_rate"]

        # OE0101D2 = Skattesats till kommun (municipal tax rate only)
        query = {
            "query": [
                {
                    "code": "Region",
                    "selection": {
                        "filter": "all",
                        "values": ["*"]
                    }
                },
                {
                    "code": "ContentsCode",
                    "selection": {
                        "filter": "item",
                        "values": ["OE0101D2"]  # Municipal tax rate
                    }
                },
                {
                    "code": "Tid",
                    "selection": {
                        "filter": "item",
                        "values": YEARS_STR
                    }
                }
            ],
            "response": {"format": "json"}
        }

        data = self._make_request(url, query, table_name)
        self._save_raw_response(data, table_name)

        df = self._parse_json_stat(data)

        if df.empty:
            logger.warning("Tax rate query returned empty data")
            return df

        # Standardize column names
        df = df.rename(columns={
            "Region": "municipality_code",
            "Tid": "year"
        })

        df["municipality_name"] = df["municipality_code"].map(MUNICIPALITIES)

        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        self._save_to_cache(df, table_name)

        time.sleep(REQUEST_DELAY)

        return df

    def fetch_all(self) -> Dict[str, pd.DataFrame]:
        """
        Fetch all required data from SCB API.

        Returns:
            Dictionary with keys: balance_sheet, population, tax_base,
            income_statement, tax_rate
        """
        logger.info("Starting to fetch all SCB data...")

        results = {}

        try:
            logger.info("Fetching balance sheet data...")
            results["balance_sheet"] = self.fetch_balance_sheet()

            logger.info("Fetching population data...")
            results["population"] = self.fetch_population_by_age()

            logger.info("Fetching tax base data...")
            results["tax_base"] = self.fetch_tax_base()

            logger.info("Fetching income statement data...")
            results["income_statement"] = self.fetch_income_statement()

            logger.info("Fetching tax rate data...")
            results["tax_rate"] = self.fetch_tax_rate()

            logger.info("Successfully fetched all SCB data")

            # Log summary statistics
            for name, df in results.items():
                logger.info(f"  {name}: {len(df)} rows, {df['municipality_code'].nunique()} municipalities")

        except SCBAPIError as e:
            logger.error(f"Failed to fetch SCB data: {e}")
            raise

        return results

    def clear_cache(self) -> None:
        """Clear all cached data files."""
        for cache_file in self.cache_dir.glob("*.parquet"):
            cache_file.unlink()
            logger.info(f"Deleted cache file: {cache_file}")

        logger.info("Cache cleared")


class KoladaFetcher:
    """
    Client for fetching data from Kolada API.

    Kolada is a database of key performance indicators (KPIs) for Swedish
    municipalities, maintained by RKA (Rådet för främjande av kommunala analyser).

    Primary use: Fetching unemployment data (from Arbetsförmedlingen via Kolada).

    Attributes:
        cache_dir: Directory for caching fetched data
        raw_dir: Directory for saving raw API responses
    """

    def __init__(
        self,
        cache_dir: str = CACHE_DIR,
        raw_dir: str = RAW_DIR,
        use_cache: bool = True
    ):
        """
        Initialize the Kolada API fetcher.

        Args:
            cache_dir: Directory path for cache files
            raw_dir: Directory path for raw data files
            use_cache: Whether to use cached data if available
        """
        self.cache_dir = Path(cache_dir)
        self.raw_dir = Path(raw_dir)
        self.use_cache = use_cache
        self.base_url = KOLADA_API_BASE

        # Create directories if they don't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json"
        })

    def _make_request(self, url: str, table_name: str) -> Dict[str, Any]:
        """
        Make a GET request to the Kolada API with retry logic.

        Args:
            url: API endpoint URL
            table_name: Name of the data being fetched for logging

        Returns:
            JSON response data

        Raises:
            KoladaAPIError: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Fetching {table_name} from Kolada API (attempt {attempt + 1}/{MAX_RETRIES})")
                logger.debug(f"URL: {url}")

                response = self.session.get(url, timeout=REQUEST_TIMEOUT)

                if response.status_code == 200:
                    logger.info(f"Successfully fetched {table_name}")
                    return response.json()
                elif response.status_code == 429:
                    wait_time = RETRY_BACKOFF_FACTOR ** (attempt + 2)
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    raise KoladaAPIError(f"API returned status {response.status_code}: {response.text}")

            except requests.exceptions.Timeout:
                last_exception = KoladaAPIError(f"Request timeout after {REQUEST_TIMEOUT}s")
                logger.warning(f"Timeout on attempt {attempt + 1}")
            except requests.exceptions.RequestException as e:
                last_exception = KoladaAPIError(f"Request failed: {str(e)}")
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")

            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF_FACTOR ** attempt
                logger.info(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        raise last_exception or KoladaAPIError(f"Failed to fetch {table_name} after {MAX_RETRIES} attempts")

    def _get_cache_path(self, table_name: str) -> Path:
        """Get the cache file path for a table."""
        return self.cache_dir / f"kolada_{table_name}.parquet"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is not expired."""
        if not cache_path.exists():
            return False

        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age_days = (datetime.now() - file_time).days

        return age_days < CACHE_EXPIRY_DAYS

    def _save_to_cache(self, df: pd.DataFrame, table_name: str) -> None:
        """Save DataFrame to cache as parquet file."""
        cache_path = self._get_cache_path(table_name)
        df.to_parquet(cache_path, index=False)
        logger.info(f"Saved {table_name} to cache: {cache_path}")

    def _load_from_cache(self, table_name: str) -> Optional[pd.DataFrame]:
        """Load DataFrame from cache if valid."""
        cache_path = self._get_cache_path(table_name)

        if self.use_cache and self._is_cache_valid(cache_path):
            logger.info(f"Loading {table_name} from cache: {cache_path}")
            return pd.read_parquet(cache_path)

        return None

    def _save_raw_response(self, data: Dict[str, Any], table_name: str) -> None:
        """Save raw API response for debugging/reproducibility."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_path = self.raw_dir / f"kolada_{table_name}_{timestamp}.json"

        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"Saved raw response to: {raw_path}")

    def search_kpi(self, title: str) -> List[Dict[str, Any]]:
        """
        Search for KPIs by title.

        Args:
            title: Search term for KPI title

        Returns:
            List of matching KPI dictionaries with id, title, description
        """
        url = f"{self.base_url}kpi?title={title}"
        data = self._make_request(url, f"kpi_search_{title}")

        kpis = data.get("values", [])
        logger.info(f"Found {len(kpis)} KPIs matching '{title}'")

        # Filter for municipality-level KPIs
        municipality_kpis = [
            kpi for kpi in kpis
            if kpi.get("municipality_type") == "K"  # K = kommun (municipality)
        ]

        logger.info(f"Found {len(municipality_kpis)} municipality-level KPIs")

        return municipality_kpis

    def fetch_kpi_data(
        self,
        kpi_id: str,
        years: Optional[List[int]] = None
    ) -> pd.DataFrame:
        """
        Fetch data for a specific KPI for all municipalities.

        Args:
            kpi_id: Kolada KPI identifier
            years: List of years to fetch (default: START_YEAR to END_YEAR)

        Returns:
            DataFrame with columns: municipality_code, year, value
        """
        if years is None:
            years = YEARS

        years_str = ",".join(str(y) for y in years)

        # Kolada API allows fetching all municipalities at once
        url = f"{self.base_url}data/kpi/{kpi_id}/year/{years_str}"

        data = self._make_request(url, f"kpi_{kpi_id}")
        self._save_raw_response(data, f"kpi_{kpi_id}")

        # Parse response
        values = data.get("values", [])

        if not values:
            logger.warning(f"No data found for KPI {kpi_id}")
            return pd.DataFrame(columns=["municipality_code", "year", "value"])

        rows = []
        for item in values:
            municipality = item.get("municipality", "")
            period = item.get("period", "")

            # Get the value - Kolada returns values array with gender breakdown
            # We want the total (gender = "T")
            item_values = item.get("values", [])

            for val in item_values:
                if val.get("gender") == "T":  # Total
                    rows.append({
                        "municipality_code": municipality,
                        "year": int(period) if period else None,
                        "value": val.get("value")
                    })
                    break
            else:
                # If no total, use first available value
                if item_values:
                    rows.append({
                        "municipality_code": municipality,
                        "year": int(period) if period else None,
                        "value": item_values[0].get("value")
                    })

        df = pd.DataFrame(rows)

        # Add municipality names
        df["municipality_name"] = df["municipality_code"].map(MUNICIPALITIES)

        return df

    def fetch_unemployment(self) -> pd.DataFrame:
        """
        Fetch unemployment data for all municipalities.

        Tries known Kolada KPIs for unemployment data. Falls back to
        alternative KPIs if primary is unavailable.

        Returns:
            DataFrame with columns: municipality_code, municipality_name, year, unemployment_pct
        """
        table_name = "unemployment"

        # Check cache first
        cached = self._load_from_cache(table_name)
        if cached is not None:
            return cached

        df = None

        # Try known unemployment KPIs in order of preference
        for kpi_id in KOLADA_UNEMPLOYMENT_KPIS:
            try:
                logger.info(f"Trying unemployment KPI: {kpi_id}")
                df = self.fetch_kpi_data(kpi_id)

                if not df.empty and df["value"].notna().sum() > 0:
                    logger.info(f"Successfully fetched unemployment data using KPI {kpi_id}")
                    break

            except KoladaAPIError as e:
                logger.warning(f"Failed to fetch KPI {kpi_id}: {e}")
                continue

        # If known KPIs failed, search for unemployment KPI
        if df is None or df.empty:
            logger.info("Known KPIs failed, searching for unemployment KPIs...")

            search_results = self.search_kpi("arbetslöshet")

            for kpi in search_results[:5]:  # Try first 5 results
                try:
                    kpi_id = kpi.get("id")
                    logger.info(f"Trying KPI: {kpi_id} - {kpi.get('title')}")

                    df = self.fetch_kpi_data(kpi_id)

                    if not df.empty and df["value"].notna().sum() > 0:
                        logger.info(f"Successfully fetched unemployment data using KPI {kpi_id}")
                        break

                except KoladaAPIError as e:
                    logger.warning(f"Failed to fetch KPI {kpi_id}: {e}")
                    continue

        if df is None or df.empty:
            raise KoladaAPIError("Failed to fetch unemployment data from any source")

        # Rename value column
        df = df.rename(columns={"value": "unemployment_pct"})

        # Ensure correct types
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["unemployment_pct"] = pd.to_numeric(df["unemployment_pct"], errors="coerce")

        # Filter to our year range
        df = df[(df["year"] >= START_YEAR) & (df["year"] <= END_YEAR)]

        # Save to cache
        self._save_to_cache(df, table_name)

        time.sleep(REQUEST_DELAY)

        return df

    def clear_cache(self) -> None:
        """Clear all Kolada cached data files."""
        for cache_file in self.cache_dir.glob("kolada_*.parquet"):
            cache_file.unlink()
            logger.info(f"Deleted cache file: {cache_file}")

        logger.info("Kolada cache cleared")


# Convenience functions for quick data fetching
def fetch_scb_data(use_cache: bool = True) -> Dict[str, pd.DataFrame]:
    """
    Convenience function to fetch all SCB data.

    Args:
        use_cache: Whether to use cached data if available

    Returns:
        Dictionary of DataFrames with all SCB data
    """
    fetcher = SCBFetcher(use_cache=use_cache)
    return fetcher.fetch_all()


def fetch_kolada_unemployment(use_cache: bool = True) -> pd.DataFrame:
    """
    Convenience function to fetch unemployment data from Kolada.

    Args:
        use_cache: Whether to use cached data if available

    Returns:
        DataFrame with unemployment data
    """
    fetcher = KoladaFetcher(use_cache=use_cache)
    return fetcher.fetch_unemployment()


def fetch_all_data(use_cache: bool = True) -> Dict[str, pd.DataFrame]:
    """
    Fetch all required data from SCB and Kolada APIs.

    Args:
        use_cache: Whether to use cached data if available

    Returns:
        Dictionary with all DataFrames needed for KRI computation:
        - balance_sheet, population, tax_base, income_statement, tax_rate (from SCB)
        - unemployment (from Kolada)
    """
    logger.info("Fetching all data from SCB and Kolada...")

    # Fetch SCB data
    scb_fetcher = SCBFetcher(use_cache=use_cache)
    results = scb_fetcher.fetch_all()

    # Fetch Kolada unemployment data
    kolada_fetcher = KoladaFetcher(use_cache=use_cache)
    results["unemployment"] = kolada_fetcher.fetch_unemployment()

    logger.info("Successfully fetched all data")
    logger.info(f"  unemployment: {len(results['unemployment'])} rows, "
                f"{results['unemployment']['municipality_code'].nunique()} municipalities")

    return results


if __name__ == "__main__":
    # Test the fetcher
    logging.getLogger().setLevel(logging.DEBUG)

    fetcher = SCBFetcher(use_cache=False)

    print("Testing SCB API fetcher...")
    print("-" * 50)

    # Test each endpoint
    try:
        print("\n1. Fetching balance sheet...")
        df_balance = fetcher.fetch_balance_sheet()
        print(f"   Rows: {len(df_balance)}")
        print(f"   Municipalities: {df_balance['municipality_code'].nunique()}")
        print(f"   Years: {df_balance['year'].min()} - {df_balance['year'].max()}")
        print(f"   Sample:\n{df_balance.head()}")

        print("\n2. Fetching population...")
        df_pop = fetcher.fetch_population_by_age()
        print(f"   Rows: {len(df_pop)}")
        print(f"   Municipalities: {df_pop['municipality_code'].nunique()}")

        print("\n3. Fetching tax base...")
        df_tax = fetcher.fetch_tax_base()
        print(f"   Rows: {len(df_tax)}")

        print("\n4. Fetching income statement...")
        df_income = fetcher.fetch_income_statement()
        print(f"   Rows: {len(df_income)}")

        print("\n5. Fetching tax rate...")
        df_rate = fetcher.fetch_tax_rate()
        print(f"   Rows: {len(df_rate)}")

        print("\n" + "=" * 50)
        print("All tests passed!")

    except Exception as e:
        print(f"Error: {e}")
        raise
