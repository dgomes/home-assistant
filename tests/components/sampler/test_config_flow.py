"""Test the sampler config flow."""
from unittest.mock import AsyncMock

import pytest

from homeassistant import config_entries
from homeassistant.components.sampler.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

pytestmark = pytest.mark.usefixtures("mock_setup_entry")


@pytest.mark.parametrize("platform", ("sensor",))
async def test_config_flow(
    hass: HomeAssistant, mock_setup_entry: AsyncMock, platform
) -> None:
    """Test the config flow."""
    input_sensor_entity_id = "sensor.input"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "My sampler", "entity_id": input_sensor_entity_id, "period": 5},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "My sampler"
    assert result["data"] == {}
    assert result["options"] == {
        "entity_id": input_sensor_entity_id,
        "name": "My sampler",
        "period": 5,
    }
    assert len(mock_setup_entry.mock_calls) == 1

    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert config_entry.data == {}
    assert config_entry.options == {
        "entity_id": input_sensor_entity_id,
        "name": "My sampler",
        "period": 5,
    }
    assert config_entry.title == "My sampler"


def get_suggested(schema, key):
    """Get suggested value for key in voluptuous schema."""
    for k in schema:
        if k == key:
            if k.description is None or "suggested_value" not in k.description:
                return None
            return k.description["suggested_value"]
    # Wanted key absent from schema
    raise Exception


@pytest.mark.parametrize("platform", ("sensor",))
async def test_options(hass: HomeAssistant, platform) -> None:
    """Test reconfiguring."""
    input_sensor_1_entity_id = "sensor.input1"

    # Setup the config entry
    config_entry = MockConfigEntry(
        data={},
        domain=DOMAIN,
        options={
            "entity_id": input_sensor_1_entity_id,
            "name": "My sampler",
            "period": 5,
        },
        title="My sampler",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    assert get_suggested(schema, "period") == 5

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    assert get_suggested(schema, "period") == 5

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "period": 10,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "entity_id": input_sensor_1_entity_id,
        "name": "My sampler",
        "period": 10,
    }
    assert config_entry.data == {}
    assert config_entry.options == {
        "entity_id": input_sensor_1_entity_id,
        "name": "My sampler",
        "period": 10,
    }
    assert config_entry.title == "My sampler"
