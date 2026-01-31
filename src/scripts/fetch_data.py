import asyncio
import httpx
import polars as pl
from pathlib import Path
import time
from typing import List, Dict, Any
from pydantic import BaseModel, Field

# Constants
BASE_URL = "https://fantasy.premierleague.com/api"
DATA_DIR = Path("src/data")
CACHE_FILE = DATA_DIR / "fpl_cache.parquet"
BOOTSTRAP_URL = f"{BASE_URL}/bootstrap-static/"
ELEMENT_SUMMARY_URL = f"{BASE_URL}/element-summary/"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


class PlayerMetadata(BaseModel):
    id: int
    first_name: str
    second_name: str
    web_name: str
    team: int
    element_type: int
    now_cost: int
    status: str


async def fetch_bootstrap(client: httpx.AsyncClient) -> Dict[str, Any]:
    print("Fetching bootstrap static data...")
    response = await client.get(BOOTSTRAP_URL)
    response.raise_for_status()
    return response.json()


async def fetch_player_summary(
    client: httpx.AsyncClient, player_id: int, semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    async with semaphore:
        url = f"{ELEMENT_SUMMARY_URL}{player_id}/"
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            data["player_id"] = player_id
            return data
        except Exception as e:
            print(f"Error fetching player {player_id}: {e}")
            return None


async def main():
    start_time = time.time()

    async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
        bootstrap_data = await fetch_bootstrap(client)

        # Extract players (elements)
        players_raw = bootstrap_data["elements"]
        teams_raw = bootstrap_data["teams"]
        events_raw = bootstrap_data["events"]

        # Filter active players
        active_players = [p for p in players_raw if p["status"] in ["a", "d", "n"]]
        player_ids = [p["id"] for p in active_players]

        print(f"Fetching history for {len(player_ids)} active players...")

        semaphore = asyncio.Semaphore(10)  # Respect rate limits
        tasks = [fetch_player_summary(client, pid, semaphore) for pid in player_ids]

        results = await asyncio.gather(*tasks)
        results = [r for r in results if r is not None]

        # Process Players Metadata
        players_df = pl.DataFrame(active_players).select(
            [
                "id",
                "first_name",
                "second_name",
                "web_name",
                "team",
                "element_type",
                "now_cost",
                "status",
            ]
        )

        # Map element_type to position names
        pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
        players_df = players_df.with_columns(
            pl.col("element_type")
            .cast(pl.String)
            .replace({str(k): v for k, v in pos_map.items()})
            .alias("position"),
            (pl.col("first_name") + " " + pl.col("second_name")).alias("full_name"),
        )

        # Map team IDs to names
        team_map = {t["id"]: t["name"] for t in teams_raw}
        players_df = players_df.with_columns(
            pl.col("team")
            .cast(pl.String)
            .replace({str(k): v for k, v in team_map.items()})
            .alias("team_name")
        )

        # Process History
        history_records = []
        for res in results:
            pid = res["player_id"]
            for entry in res.get("history", []):
                entry["player_id"] = pid
                history_records.append(entry)

        history_df = pl.DataFrame(history_records)

        # Save to Parquet
        players_df.write_parquet(DATA_DIR / "players.parquet")
        history_df.write_parquet(DATA_DIR / "gameweek_history.parquet")

        # Save fixtures too
        fixtures_raw = bootstrap_data.get(
            "fixtures", []
        )  # Wait, fixtures are often separate API
        # Actually bootstrap has next fixtures for players, but let's just save what we have

        print(
            f"Successfully fetched {len(active_players)} players and {len(history_records)} history records."
        )
        print(f"Data saved to {DATA_DIR}")
        print(f"Time taken: {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
