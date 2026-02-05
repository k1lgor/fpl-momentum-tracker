"""
Unit tests for the momentum analysis engine.
"""

import pytest
import polars as pl
import numpy as np
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scripts.analyze_momentum import calculate_momentum_score


class TestCalculateMomentumScore:
    """Test suite for the calculate_momentum_score function."""

    def test_momentum_with_valid_increasing_data(self):
        """Should return positive score for increasing values."""
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        score = calculate_momentum_score(y)
        assert score > 0, "Score should be positive for increasing data"
        # For perfectly linear data, R^2 = 1.0, so score == slope
        assert abs(score - 1.0) < 0.01, (
            f"Score should be approximately 1.0, got {score}"
        )

    def test_momentum_with_valid_decreasing_data(self):
        """Should return negative score for decreasing values."""
        y = [5.0, 4.0, 3.0, 2.0, 1.0]
        score = calculate_momentum_score(y)
        assert score < 0, "Score should be negative for decreasing data"
        assert abs(score + 1.0) < 0.01, "Score should be approximately -1.0"

    def test_momentum_with_flat_data(self):
        """Should return zero score for constant values."""
        y = [3.0, 3.0, 3.0, 3.0]
        score = calculate_momentum_score(y)
        assert abs(score) < 0.01, "Score should be approximately zero for flat data"

    def test_momentum_with_insufficient_data(self):
        """Should return 0.0 for insufficient data (< 3 points)."""
        y = [5.0, 6.0]
        score = calculate_momentum_score(y)
        assert score == 0.0, "Should return 0.0 for insufficient data"

    def test_momentum_with_empty_list(self):
        """Should return 0.0 for empty list."""
        y = []
        score = calculate_momentum_score(y)
        assert score == 0.0, "Should return 0.0 for empty list"

    def test_momentum_with_none_values(self):
        """Should handle None values gracefully."""
        y = [1.0, None, 2.0, None, 3.0, None, 4.0, None, 5.0]
        score = calculate_momentum_score(y)
        assert score > 0, "Should handle None values and return positive score"

    def test_momentum_with_nan_values(self):
        """Should handle NaN values gracefully."""
        y = [1.0, np.nan, 2.0, np.nan, 3.0, np.nan, 4.0, np.nan, 5.0]
        score = calculate_momentum_score(y)
        assert score > 0, "Should handle NaN values and return positive score"

    def test_momentum_with_all_none(self):
        """Should return 0.0 when all values are None."""
        y = [None, None, None]
        score = calculate_momentum_score(y)
        assert score == 0.0, "Should return 0.0 when all values are None"

    def test_momentum_preserves_temporal_alignment(self):
        """
        CRITICAL TEST: Ensure temporal alignment is preserved when filtering None/NaN.
        """
        # Sequence: [1.0, None, 2.0, None, 3.0]
        # Valid pairs should be: (0, 1.0), (2, 2.0), (4, 3.0)
        y = [1.0, None, 2.0, None, 3.0]
        score = calculate_momentum_score(y)

        # Expected slope: (3.0 - 1.0) / (4 - 0) = 0.5
        # R^2 for perfectly linear data is 1.0
        assert abs(score - 0.5) < 0.01, f"Expected score ~0.5, got {score}"


class TestMomentumAnalysisIntegration:
    """Integration tests for the full momentum analysis pipeline."""

    @pytest.fixture
    def sample_players_df(self):
        """Create a sample players dataframe for testing."""
        return pl.DataFrame(
            {
                "id": [1, 2, 3],
                "first_name": ["Mohamed", "Erling", "Bukayo"],
                "second_name": ["Salah", "Haaland", "Saka"],
                "web_name": ["Salah", "Haaland", "Saka"],
                "team": [1, 2, 3],
                "element_type": [3, 4, 3],
                "now_cost": [130, 145, 95],
                "status": ["a", "a", "a"],
                "position": ["MID", "FWD", "MID"],
                "full_name": ["Mohamed Salah", "Erling Haaland", "Bukayo Saka"],
                "team_name": ["Liverpool", "Man City", "Arsenal"],
            }
        )

    @pytest.fixture
    def sample_history_df(self):
        """Create a sample gameweek history for testing."""
        # Create 10 gameweeks for 3 players
        data = []
        for player_id in [1, 2, 3]:
            for gw in range(1, 11):
                data.append(
                    {
                        "player_id": player_id,
                        "round": gw,
                        "minutes": 90 if gw > 2 else 0,  # First 2 GWs no play
                        "goals_scored": 1 if gw % 3 == 0 else 0,
                        "expected_goals": 0.5 + (gw * 0.1),  # Increasing xG
                        "expected_assists": 0.3,
                        "expected_goal_involvements": 0.8,
                        "expected_goals_conceded": 1.2,
                        "clean_sheets": 1 if gw % 4 == 0 else 0,
                        "goals_conceded": 1,
                        "tackles": 2,
                        "recoveries": 4,
                        "clearances_blocks_interceptions": 3,
                        "saves": 0,
                        "influence": "50.0",
                        "creativity": "40.0",
                        "threat": "60.0",
                        "ict_index": "15.0",
                    }
                )
        return pl.DataFrame(data)

    def test_data_processing_pipeline(self, sample_players_df, sample_history_df):
        """Test that the data processing pipeline handles sample data correctly."""
        # Join players and history
        df = sample_history_df.join(
            sample_players_df, left_on="player_id", right_on="id"
        )

        assert df.shape[0] == 30, "Should have 30 rows (3 players × 10 gameweeks)"
        assert "web_name" in df.columns, "Should have player name after join"
        assert "position" in df.columns, "Should have position after join"

    def test_xgi_per_90_calculation(self, sample_history_df):
        """Test xGI per 90 calculation logic."""
        df = sample_history_df.with_columns(
            pl.when(pl.col("minutes") > 0)
            .then(pl.col("expected_goal_involvements") * 90 / pl.col("minutes"))
            .otherwise(0)
            .alias("xgi_per_90_per_game")
        )

        # Check that xGI/90 is 0 when minutes is 0
        zero_minutes = df.filter(pl.col("minutes") == 0)
        assert (zero_minutes["xgi_per_90_per_game"] == 0).all(), (
            "xGI/90 should be 0 when minutes is 0"
        )

        # Check that xGI/90 equals xGI when minutes is 90
        full_minutes = df.filter(pl.col("minutes") == 90)
        assert (
            full_minutes["xgi_per_90_per_game"]
            == full_minutes["expected_goal_involvements"]
        ).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
