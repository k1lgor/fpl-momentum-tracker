import asyncio
import httpx
import polars as pl
from pathlib import Path
import time
from typing import Dict, Any
from pydantic import BaseModel

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
    """
    Main function to fetch FPL data from the official API.

    Fetches bootstrap data, player metadata, and gameweek history.
    Saves processed data to parquet files in the data directory.
    """
    start_time = time.time()

    try:
        async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
            # Fetch bootstrap data with error handling
            try:
                bootstrap_data = await fetch_bootstrap(client)
            except httpx.HTTPError as e:
                print(f"❌ Failed to fetch bootstrap data: {e}")
                print("Please check your internet connection and try again.")
                return
            except Exception as e:
                print(f"❌ Unexpected error fetching bootstrap data: {e}")
                return

            # Validate bootstrap data structure
            if not all(
                key in bootstrap_data for key in ["elements", "teams", "events"]
            ):
                print("❌ Invalid bootstrap data structure received from API")
                return

            # Extract players (elements)
            players_raw = bootstrap_data["elements"]
            teams_raw = bootstrap_data["teams"]
            # events_raw could be used for future gameweek analysis

            if not players_raw:
                print("❌ No player data found in API response")
                return

            # Filter active players
            active_players = [p for p in players_raw if p["status"] in ["a", "d", "n"]]
            player_ids = [p["id"] for p in active_players]

            print(f"✅ Found {len(active_players)} active players")
            print(f"📥 Fetching detailed history for {len(player_ids)} players...")

            # Fetch player summaries with rate limiting
            semaphore = asyncio.Semaphore(10)  # Respect rate limits
            tasks = [fetch_player_summary(client, pid, semaphore) for pid in player_ids]

            results = await asyncio.gather(*tasks)
            results = [r for r in results if r is not None]

            failed_count = len(player_ids) - len(results)
            if failed_count > 0:
                print(f"⚠️  Failed to fetch data for {failed_count} players")

            # Process Players Metadata
            try:
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
                    (pl.col("first_name") + " " + pl.col("second_name")).alias(
                        "full_name"
                    ),
                )

                # Map team IDs to names
                team_map = {t["id"]: t["name"] for t in teams_raw}
                players_df = players_df.with_columns(
                    pl.col("team")
                    .cast(pl.String)
                    .replace({str(k): v for k, v in team_map.items()})
                    .alias("team_name")
                )
            except Exception as e:
                print(f"❌ Error processing player metadata: {e}")
                return

            # Process History
            try:
                history_records = []
                for res in results:
                    pid = res["player_id"]
                    for entry in res.get("history", []):
                        entry["player_id"] = pid
                        history_records.append(entry)

                if not history_records:
                    print(
                        "⚠️  No gameweek history found. This might be early in the season."
                    )
                    # Still save player data even if no history
                    history_df = pl.DataFrame()
                else:
                    history_df = pl.DataFrame(history_records)
                    print(f"✅ Processed {len(history_records)} gameweek records")
            except Exception as e:
                print(f"❌ Error processing gameweek history: {e}")
                return

            # Save to Parquet
            try:
                players_df.write_parquet(DATA_DIR / "players.parquet")
                if not history_df.is_empty():
                    history_df.write_parquet(DATA_DIR / "gameweek_history.parquet")

                print(f"✅ Successfully saved data to {DATA_DIR}")
                print(f"   - {len(active_players)} players")
                print(f"   - {len(history_records)} gameweek records")
                print(f"⏱️  Time taken: {time.time() - start_time:.2f}s")
            except Exception as e:
                print(f"❌ Error saving data to parquet: {e}")
                return

    except Exception as e:
        print(f"❌ Unexpected error in main function: {e}")
        import traceback

        traceback.print_exc()
        return


if __name__ == "__main__":
    asyncio.run(main())
