"""Calendar platform for MedAdvisor."""

from __future__ import annotations

import logging
import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription

from .const import DOMAIN
from .coordinator import MaDataUpdateCoordinator
from .entity import MaEntity


ENTITY_DESCRIPTIONS = (
    EntityDescription(
        key="calendar",
        name="Prescriptions",
        icon="mdi:pill",
    ),
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the calendar platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        MaCalendar(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )


class MaCalendar(MaEntity, CalendarEntity):
    """MedAdvisor Calendar class."""

    def __init__(
        self,
        coordinator: MaDataUpdateCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """Initialize the calendar class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._event: CalendarEvent | None = None

    @property
    def event(self) -> CalendarEvent:
        """Return the next upcoming event."""
        if self.coordinator.data and self.coordinator.data["prescription"]:
            _LOGGER.debug("Found event")
            self._event = CalendarEvent(
                start=self.coordinator.data["prescription"]["start"],
                end=self.coordinator.data["prescription"]["end"],
                summary=self.coordinator.data["prescription"]["summary"],
                description=self.coordinator.data["prescription"]["description"],
                location=self.coordinator.data["prescription"]["location"],
            )
        else:
            _LOGGER.debug("No events found")
            self._event = None
        return self._event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> list[CalendarEvent]:
        """Return calendar events within a datetime range."""
        """ # not sure this is required
        assert start_date < end_date
        if self._event.start_datetime_local >= end_date:
            return []
        if self._event.end_datetime_local < start_date:
            return []
        """
        return [self._event]
