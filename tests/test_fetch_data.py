"""
Unit tests for the FPL data fetcher.
"""

import pytest
import polars as pl
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scripts.fetch_data import PlayerMetadata


class TestPlayerMetadata:
    """Test suite for PlayerMetadata Pydantic model."""

    def test_valid_player_metadata(self):
        """Should create valid PlayerMetadata from correct data."""
        data = {
            "id": 1,
            "first_name": "Mohamed",
            "second_name": "Salah",
            "web_name": "Salah",
            "team": 14,
            "element_type": 3,
            "now_cost": 130,
            "status": "a",
        }
        player = PlayerMetadata(**data)
        assert player.id == 1
        assert player.web_name == "Salah"
        assert player.status == "a"

    def test_missing_required_field(self):
        """Should raise validation error when required field is missing."""
        data = {
            "id": 1,
            "first_name": "Mohamed",
            # Missing second_name
            "web_name": "Salah",
            "team": 14,
            "element_type": 3,
            "now_cost": 130,
            "status": "a",
        }
        with pytest.raises(Exception):  # Pydantic ValidationError
            PlayerMetadata(**data)

    def test_invalid_type(self):
        """Should raise validation error when field has wrong type."""
        data = {
            "id": "not_an_int",  # Should be int
            "first_name": "Mohamed",
            "second_name": "Salah",
            "web_name": "Salah",
            "team": 14,
            "element_type": 3,
            "now_cost": 130,
            "status": "a",
        }
        with pytest.raises(Exception):  # Pydantic ValidationError
            PlayerMetadata(**data)


class TestDataValidation:
    """Test data validation and transformation logic."""

    def test_position_mapping(self):
        """Test that element_type correctly maps to position names."""
        pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

        df = pl.DataFrame(
            {
                "element_type": [1, 2, 3, 4],
            }
        )

        df = df.with_columns(
            pl.col("element_type")
            .cast(pl.String)
            .replace({str(k): v for k, v in pos_map.items()})
            .alias("position")
        )

        assert df["position"].to_list() == ["GKP", "DEF", "MID", "FWD"]

    def test_full_name_creation(self):
        """Test that full_name is correctly created from first and last name."""
        df = pl.DataFrame(
            {
                "first_name": ["Mohamed", "Erling"],
                "second_name": ["Salah", "Haaland"],
            }
        )

        df = df.with_columns(
            (pl.col("first_name") + " " + pl.col("second_name")).alias("full_name")
        )

        assert df["full_name"].to_list() == ["Mohamed Salah", "Erling Haaland"]

    def test_active_player_filtering(self):
        """Test that only active players are included."""
        players = [
            {"id": 1, "status": "a"},  # Available
            {"id": 2, "status": "d"},  # Doubtful
            {"id": 3, "status": "i"},  # Injured - should be excluded
            {"id": 4, "status": "n"},  # Not available for next gameweek
            {"id": 5, "status": "s"},  # Suspended - should be excluded
        ]

        active_statuses = ["a", "d", "n"]
        active_players = [p for p in players if p["status"] in active_statuses]

        assert len(active_players) == 3
        assert all(p["status"] in active_statuses for p in active_players)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
