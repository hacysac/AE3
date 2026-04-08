from datetime import date, datetime, time
from typing import Iterator, List, Dict, Any
import requests
from requests.exceptions import HTTPError, RequestException, Timeout


class Observation:
    """
    Represents a 15 minute observation of traffic for a specific site, date, and time.
    """

    # required attributes
    site_name: str
    report_date: date
    time_period_ending: time
    avg_speed: int | None
    total_volume: int | None

    def __init__(
        self,
        site_name: str,
        report_date: date,
        time_period_ending: time,
        avg_speed: int | None,
        total_volume: int | None,
    ) -> None:
        """
        Creates an Observation with the site name, report date, time period ending, average speed, and total vehicle volume.
        """
        self.site_name = site_name
        self.report_date = report_date
        self.time_period_ending = time_period_ending
        self.avg_speed = avg_speed
        self.total_volume = total_volume

    def valid_volume(self) -> bool:
        """
        Checks if the observation contains valid volume data.
        """
        return self.total_volume is not None

    def valid_speed(self) -> bool:
        """
        Checks if the observation contains valid speed data.
        """
        return self.avg_speed is not None

    def is_valid(self) -> bool:
        """
        Checks if the observation contains complete data (not missing volume or speed).
        """
        return self.valid_volume() and self.valid_speed()

    def __lt__(self, other: "Observation") -> bool:
        """
        Checks if this observation occurs before the other, comparing first by date and then by time.
        """
        if self.report_date != other.report_date:
            return self.report_date < other.report_date
        return self.time_period_ending < other.time_period_ending

    def __eq__(self, other: "Observation") -> bool:
        """
        Checks if two observations share the same site name, report date, and time period ending.
        """
        return (
            self.report_date == other.report_date
            and self.time_period_ending == other.time_period_ending
            and self.site_name == other.site_name
        )

    def __repr__(self) -> str:
        """
        Returns a string representation of the observation including all attributes.
        """
        return f"Observation(name={self.site_name}, date={self.report_date}, time={self.time_period_ending}, speed={self.avg_speed}, volume={self.total_volume})"


class APIConnector:
    """
    Handles making API requests and API errors
    """

    def make_request(self, url: str) -> Dict[str, Any]:
        """
        Makes a get request to the API and returns the JSON as a dictionary
        """
        try:
            # attempt to make the API request with a timeout of 10 seconds
            response = requests.get(url, timeout=10)

            # check for errors from site call
            if (
                response.status_code == 201
            ):  # not technically and error but we shouldnt be creating a site so treat it as one
                raise Exception("Site created (201)")
            elif (
                response.status_code == 204
            ):  # not technically an error but we should be getting data so treat it as one
                raise Exception("Site has no content (204)")
            elif response.status_code == 301:
                raise Exception("Site moved permanently (301)")
            elif response.status_code == 304:
                raise Exception("Site not modified (304)")
            elif response.status_code == 400:
                raise Exception("Bad request (400)")
            elif response.status_code == 401:
                raise Exception("Site unauthorized (401)")
            elif response.status_code == 404:
                raise Exception("Site not found (404)")
            elif response.status_code == 500:
                raise Exception("Internal server error (500)")
            elif response.status_code == 503:
                raise Exception("Service unavailable (503)")
            elif (
                response.status_code != 200
            ):  # catch any other non-success status codes
                raise Exception(f"API returned status code {response.status_code}")

            return response.json()  # return the json if no errors

        # errors if the request fails
        except Timeout:
            raise Exception("Request timed out, API may be busy")
        except HTTPError as e:
            raise Exception(f"HTTP error occurred: {e}")
        except RequestException as e:
            raise Exception(f"Network error: {e}")


class APIClient:
    """
    Functions to get and read traffic data from the Webtris API, using an APIConnector to handle the actual API requests and errors.
    """

    # base URL for all WebTRIS requests
    url = "https://webtris.nationalhighways.co.uk/api/v1.0/reports/daily?"
    connector: APIConnector

    def __init__(self, connector: APIConnector) -> None:
        """
        Creates the APIClient with an APIConnector to make requests.
        """
        self.connector = connector

    def get_daily_data(self, site_id: int, date: str) -> List[Observation]:
        """
        Validates the date, gets daily traffi`````c data for the given site, and returns a sorted list of Observation objects.
        """
        self.check_date_format(date)
        url = self.make_url(site_id, date, date)
        json_data = self.connector.make_request(url)
        observations = self.read_json_response(json_data)
        observations.sort()

        return observations

    def make_url(self, site_id: int, start_date: str, end_date: str) -> str:
        """
        Makes and returns the API request URL using the given site ID and date range.
        """
        params = f"sites={site_id}&start_date={start_date}&end_date={end_date}&page=1&page_size=500"
        return self.url + params

    def read_json_response(self, json_data: Dict[str, Any]) -> List[Observation]:
        """
        Converts a JSON response from the API into a list of Observations.
        """
        observations = []

        if "Rows" not in json_data:
            raise Exception("Invalid API response, missing 'Rows'")

        rows = json_data["Rows"]

        for row in rows:
            # required attributes for an observation
            site_name = row["Site Name"]
            report_date = self.find_date(row["Report Date"])
            time_period_ending = self.find_time(row["Time Period Ending"])
            avg_speed = self.find_int(row.get("Avg mph", ""))
            total_volume = self.find_int(row.get("Total Volume", ""))

            # create an Observation for each 15 minute interval
            observation = Observation(
                site_name=site_name,
                report_date=report_date,
                time_period_ending=time_period_ending,
                avg_speed=avg_speed,
                total_volume=total_volume,
            )

            # add the observation to the list
            observations.append(observation)

        return observations  # return the final list of observations

    def find_date(self, date_str: str) -> date:
        """
        Converts a date string from the API into a Python date object.
        """
        # API returns dates like "2025-10-19T00:00:00"
        dt = date(
            month=int(date_str[5:7]), day=int(date_str[8:10]), year=int(date_str[0:4])
        )
        return dt

    def find_time(self, time_str: str) -> time:
        """
        Converts a time string from the API into a Python time object.
        """
        # API returns times like "00:13:00"
        parts = time_str.split(":")
        return time(hour=int(parts[0]), minute=int(parts[1]), second=int(parts[2]))

    def find_int(self, value: str) -> int | None:
        """
        Attempts to convert a string from the API into an integer, returns None if the value is invalid.
        """
        try:
            return int(value)
        except ValueError:
            return None

    def check_date_format(self, date: str) -> None:
        """
        Checks that the date string is in DDMMYYYY format, represents a real date, and is within a reasonable year range.
        """
        try:
            # found on stack overflow, this will automatically fail if the date is incorrectly formatted or doesnt exist
            date_obj = datetime.strptime(date, "%d%m%Y").date()
        except ValueError:
            raise ValueError(f"Invalid date: {date}")
        # fail if the date is in the future or before 2020 (dates before 2020 don't contain valid data)
        if date_obj >= datetime.now().date() or date_obj.year < 2020:
            raise ValueError(f"Date out of reasonable range: {date_obj}")


class SingleSite:
    """
    Stores and analyses a full day of traffic observations for a single sensor site.
    """

    # required attributes
    site_id: int
    site_name: str
    observations: List[Observation]

    def __init__(self, site_id: int, site_name: str) -> None:
        """
        Creates a SingleSite with a site ID, site name, and an empty observations list.
        """
        self.site_id = site_id
        self.site_name = site_name
        self.observations = []

    def get_data(self, client: APIClient, date: str) -> None:
        """
        Uses an APIClient to get and store Observations for this site on the given date.
        """
        self.observations = client.get_daily_data(self.site_id, date)

        # update site name from observations if it exists
        if self.observations:
            self.site_name = self.observations[0].site_name

    def calculate_avg_speed(self) -> float | None:
        """
        Calculates the average speed for all observations with valid speed data.
        """
        valid_speeds = [
            observation.avg_speed
            for observation in self.observations
            if observation.valid_speed()
        ]

        if not valid_speeds:
            return None

        return sum(valid_speeds) / len(valid_speeds)

    def calculate_total_volume(self) -> int:
        """
        Calculates the total vehicle volume for all observations with valid volume data.
        """
        total = sum(
            observation.total_volume
            for observation in self.observations
            if observation.valid_volume()
        )

        return total

    def calculate_avg_speed_for_hour(self, hour: int) -> float | None:
        """
        Calculates the average speed for a specific hour.
        """
        # catch invalid hour
        if not (0 <= hour <= 23):
            raise ValueError(f"Hour must be between 0 and 23, got {hour}")

        hourly_records = [
            observation.avg_speed
            for observation in self.all_observations_for_hour(hour)
            if observation.valid_speed()
        ]

        if not hourly_records:
            return None

        return sum(hourly_records) / len(hourly_records)

    def calculate_total_volume_for_hour(self, hour: int) -> int:
        """
        Calculates the total vehicle volume for a specific hour of the day.
        """
        # catch invalid hour input
        if not (0 <= hour <= 23):
            raise ValueError(f"Hour must be between 0 and 23, got {hour}")

        hourly_records = [
            observation.total_volume
            for observation in self.all_observations_for_hour(hour)
            if observation.valid_volume()
        ]

        return sum(hourly_records)

    def all_observations_for_hour(self, hour: int) -> List[Observation]:
        """
        Returns a list of all observations within the given hour.
        """
        # catch invalid hour input
        if not (0 <= hour <= 23):
            raise ValueError(f"Hour must be between 0 and 23, got {hour}")

        return [
            observation
            for observation in self.observations
            if observation.time_period_ending.hour == hour
        ]

    def find_peak_hour(self) -> int | None:
        """
        Returns the hour with the highest total vehicle volume.
        """
        # check for observations
        if not self.observations:
            return None

        # calculate volume for each hour
        hourly_volumes = {}
        for hour in range(24):
            volume = self.calculate_total_volume_for_hour(hour)
            if volume > 0:  # Only include hours with actual traffic
                hourly_volumes[hour] = volume

        # find hour with max volume
        peak_hour = (
            max(hourly_volumes, key=hourly_volumes.get) if hourly_volumes else None
        )
        return peak_hour

    def __iter__(self) -> Iterator[Observation]:
        """
        Allows iteration over all observations.
        """
        return iter(self.observations)

    def __len__(self) -> int:
        """
        Returns the number of observations stored in this site.
        """
        return len(self.observations)
