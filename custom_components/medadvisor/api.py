"""MedAdvisor API."""

from __future__ import annotations
import logging
import base64

import asyncio
import socket

import aiohttp
import async_timeout

from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)


class MaApiError(Exception):
    """Exception to indicate a general API error."""


class MaApiCommunicationError(MaApiError):
    """Exception to indicate a communication error."""


class MaApiAuthenticationError(MaApiError):
    """Exception to indicate an authentication error."""


class MaApi:
    """MedAdvisor API."""

    def __init__(
        self,
        email: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """MedAdvisor API."""
        self._email = email
        self._password = password
        self._session = session
        self._token = None
        self._user = None
        self._server = "https://unified.medadvisor.com.au/api"

    async def login(self) -> any:
        """Login to the API."""
        response = await self._api_wrapper(
            method="post",
            url=self._server + "/v2/Account/login",
            json={
                "properties": {"source": "5", "region": 0},
                "userName": self._email,
                "password_encoded": base64.b64encode(self._password.encode()).decode(),
            },
        )

        if (
            response.get("result") == 1
            and response.get("data", {}).get("status") == "Success"
        ):
            self._token = response["data"].get("token")
            self._user = response["data"].get("properties").get("userid")
            return True
        else:
            raise MaApiAuthenticationError(
                "Invalid credentials but was this part required?",
            )
            return False

    async def get_prescriptions(self) -> any:
        """Get data from the API."""
        if not self._token:
            await self.login()

        # Get prescriptions
        _LOGGER.debug("Fetching current prescriptions")
        response = await self._api_wrapper(
            method="get",
            url=self._server + "/v1/patient/" + self._user + "/dispenserequest/verify",
            headers={"Authorization": "Bearer " + self._token},
        )

        _LOGGER.debug(f"Prescriptions data: {response}")

        if response and "data" in response and "drugs" in response["data"]:
            _LOGGER.debug("Fetched current prescriptions")

            # Loop through the prescription(s)
            for drug in response["data"]["drugs"]:
                _LOGGER.debug("Found prescription")

                # Check if lastDispense is a dictionary and contains the dispenseDate
                last_dispense = drug.get("lastDispense")
                if isinstance(last_dispense, dict) and "dispenseDate" in last_dispense:
                    dispense_date = last_dispense["dispenseDate"]
                    try:
                        # Convert the dispense date to a datetime object
                        start = datetime.strptime(
                            dispense_date + "+1300", "%Y-%m-%dT%H:%M:%S%z"
                        )
                        _LOGGER.debug(f"Dispense date parsed successfully: {start}")

                        # Calculate the end time from the duration
                        end = start + timedelta(days=last_dispense["daysSupply"])
                    except ValueError as e:
                        _LOGGER.error(f"Date parsing error: {e}")
                else:
                    _LOGGER.warning(
                        "`lastDispense` and `dispenseDate` unavailable"
                    )

                # Find the drugs name
                summary = (
                    str(drug["packetSize"])
                    + " "
                    + drug["labelName"]
                    + " "
                    + drug["strength"]
                    + " "
                    + drug["form"]
                )

                # Find the description of the drug
                description = drug["activeName"]

                # Find the repeats left
                location = (
                    str(drug["totalFillsRemaining"])
                    + " of "
                    + str(drug["totalFillsAuthorized"])
                    + " remaining"
                )

                '''
                Because we are ordering by date in the API call,
                we only ever need the first result to get the soonest prescription.
                '''
                return {
                    "prescription": {
                        "start": start,
                        "end": end,
                        "summary": summary,
                        "description": description,
                        "location": location,
                        "raw": response,
                    }
                }
        else:
            _LOGGER.error("Unexpected API response structure.")

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        json: dict | None = None,
        headers: dict | None = None,
    ) -> any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    data=data,
                    json=json,
                    headers=headers,
                )
                if response.status in (400, 401, 403):
                    raise MaApiAuthenticationError()
                response.raise_for_status()
                return await response.json()

        except MaApiAuthenticationError as exception:
            raise MaApiAuthenticationError("Invalid credentials") from exception
        except asyncio.TimeoutError as exception:
            raise MaApiCommunicationError(
                "Timeout error fetching information: %s", exception
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise MaApiCommunicationError(
                "Error fetching information: %s", exception
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise MaApiError(
                "Something really wrong happened!: %s", exception
            ) from exception

    async def disconnect(self) -> None:
        """Disconnect from the client."""
        _LOGGER.debug("Invoked close manually")
        await self.__aexit__()

    async def __aexit__(self, *excinfo):
        """Destroy the device and http sessions."""
        _LOGGER.debug("Invoked close automatically")
        if not self._session:
            return

        await self._session.close()
