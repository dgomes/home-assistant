"""Test the Entidade Reguladora dos Serviços Energéticos config flow."""
from asynctest import patch

from homeassistant import config_entries, setup
from homeassistant.components.erse.config_flow import InvalidPlan
from homeassistant.components.erse.const import DOMAIN


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.erse.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.erse.async_setup_entry", return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"operator": "EDP", "plan": "Simples"}
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "edp_simples"
    assert result2["data"] == {
        "operator": "EDP",
        "plan": "Simples",
    }
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_plan(hass):
    """Test we handle invalid plan."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.erse.config_flow.validate_input",
        side_effect=InvalidPlan,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"operator": "Galp", "plan": "Tri-horário - ciclo diário"},
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "invalid_plan"}
