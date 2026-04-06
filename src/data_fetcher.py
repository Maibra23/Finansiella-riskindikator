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
    YEARS_STR,
    POPULATION_YEARS_STR,
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
            DataFrame with columns: region, balanspost, year, value
            Value is in tkr (thousands of SEK)
        """
        table_name = "balance_sheet"

        # Check cache first
        cached = self._load_from_cache(table_name)
        if cached is not None:
            return cached

        url = SCB_API_URLS["balance_sheet"]

        # Build query for balance sheet data
        # We need to specify which balance posts to fetch
        query = {
            "query": [
                {
                    "code": "Region",
                    "selection": {
                        "filter": "vs:RegionKommun07",
                        "values": []  # All municipalities
                    }
                },
                {
                    "code": "Balanspost",
                    "selection": {
                        "filter": "item",
                        "values": list(BALANCE_SHEET_POSTS.values())
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

        # Rename columns for clarity
        df.columns = ["region", "balanspost", "year", "value"]

        # Extract municipality code from region string (format: "0180 Stockholm")
        df["municipality_code"] = df["region"].str.extract(r"^(\d{4})")
        df["municipality_name"] = df["region"].str.extract(r"^\d{4}\s+(.+)$")

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
            DataFrame with columns: region, age, year, value
        """
        table_name = "population"

        # Check cache first
        cached = self._load_from_cache(table_name)
        if cached is not None:
            return cached

        url = SCB_API_URLS["population"]

        # We need age groups for dependency ratio calculation
        # Age groups: 0-19, 20-64, 65+
        # SCB uses single ages, so we'll need to aggregate
        query = {
            "query": [
                {
                    "code": "Region",
                    "selection": {
                        "filter": "vs:RegionKommun07",
                        "values": []  # All municipalities
                    }
                },
                {
                    "code": "Kon",
                    "selection": {
                        "filter": "item",
                        "values": ["1+2"]  # Total (men + women)
                    }
                },
                {
                    "code": "Alder",
                    "selection": {
                        "filter": "agg:Ålder10LedigTotÅld",  # Age groups
                        "values": []  # All age groups
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

        # Rename columns
        df.columns = ["region", "sex", "age", "contents", "year", "value"]

        # Extract municipality code
        df["municipality_code"] = df["region"].str.extract(r"^(\d{4})")
        df["municipality_name"] = df["region"].str.extract(r"^\d{4}\s+(.+)$")

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
            DataFrame with columns: region, variable, year, value
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
                        "filter": "vs:RegionKommun07",
                        "values": []
                    }
                },
                {
                    "code": "ContentsCode",
                    "selection": {
                        "filter": "item",
                        "values": ["OE0101F2"]  # Share of national average
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
        df.columns = ["region", "variable", "year", "value"]

        df["municipality_code"] = df["region"].str.extract(r"^(\d{4})")
        df["municipality_name"] = df["region"].str.extract(r"^\d{4}\s+(.+)$")

        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        self._save_to_cache(df, table_name)

        time.sleep(REQUEST_DELAY)

        return df

    def fetch_income_statement(self) -> pd.DataFrame:
        """
        Fetch income statement data (annual result) for all municipalities.

        Returns:
            DataFrame with columns: region, resultatpost, year, value
            Value is in tkr (thousands of SEK)
        """
        table_name = "income_statement"

        # Check cache first
        cached = self._load_from_cache(table_name)
        if cached is not None:
            return cached

        url = SCB_API_URLS["income_statement"]

        query = {
            "query": [
                {
                    "code": "Region",
                    "selection": {
                        "filter": "vs:RegionKommun07",
                        "values": []
                    }
                },
                {
                    "code": "Resultatrakning",
                    "selection": {
                        "filter": "item",
                        "values": ["R11"]  # Årets resultat (Annual result)
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
        df.columns = ["region", "resultatpost", "year", "value"]

        df["municipality_code"] = df["region"].str.extract(r"^(\d{4})")
        df["municipality_name"] = df["region"].str.extract(r"^\d{4}\s+(.+)$")

        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        self._save_to_cache(df, table_name)

        time.sleep(REQUEST_DELAY)

        return df

    def fetch_tax_rate(self) -> pd.DataFrame:
        """
        Fetch municipal tax rate for all municipalities.

        Returns:
            DataFrame with columns: region, variable, year, value
            Value is tax rate in percent
        """
        table_name = "tax_rate"

        # Check cache first
        cached = self._load_from_cache(table_name)
        if cached is not None:
            return cached

        url = SCB_API_URLS["tax_rate"]

        query = {
            "query": [
                {
                    "code": "Region",
                    "selection": {
                        "filter": "vs:RegionKommun07",
                        "values": []
                    }
                },
                {
                    "code": "ContentsCode",
                    "selection": {
                        "filter": "item",
                        "values": ["OE0101D1"]  # Municipal tax rate
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
        df.columns = ["region", "variable", "year", "value"]

        df["municipality_code"] = df["region"].str.extract(r"^(\d{4})")
        df["municipality_name"] = df["region"].str.extract(r"^\d{4}\s+(.+)$")

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


# Convenience function for quick data fetching
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
