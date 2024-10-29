"""DataUpdateCoordinator for MedAdvisor."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import (
    MaApi,
    MaApiAuthenticationError,
    MaApiError,
)
from .const import DOMAIN, LOGGER


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class MaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: MaApi,
    ) -> None:
        """Initialize."""
        self.api = api
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=4),
        )

        async def disconnect() -> None:
            """Close ClientSession."""
            await self.api.disconnect()

        # Disconnect the ClientSession on stop
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, disconnect)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.api.get_prescriptions()
        except MaApiAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except MaApiError as exception:
            raise UpdateFailed(exception) from exception
