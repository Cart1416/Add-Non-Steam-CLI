# Non-Steam Game Adder

A python script to add non-steam games to your Steam library with artwork from steamgriddb

## Features
- Add non-Steam games to Steam.
- Fetch game artwork (grid, hero, logo, icon) from SteamGridDB.
- Works on Linux and Windows.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Cart1416/Add-Non-Steam-CLI.git
   cd Add-Non-Steam-CLI

2. Install dependencies:

pip install -r requirements.txt



## Usage

CLI

Run the script interactively:

python main.py



Module

Use the script in your own projects:

``` python
from Add-Non-Steam-CLI import NonSteamGameAdder

adder = NonSteamGameAdder(
    steam_user_data_path="~/.steam/steam/userdata",
    steamgriddb_api_key="your_api_key_here"
)
adder.fetch_steamgriddb_image(self, game_id, image_type)
adder.get_local_steam_usernames()
adder.add_non_steam_game(
    game_exe_path="/path/to/game",
    game_name="Game Name",
    user_id="12345678",
    launch_options=""
)
```

Dependencies

```
Python 3.7+

requests

pillow

vdf
```


Notes

Get a SteamGridDB API key from SteamGridDB for artwork.

Ensure Steam is installed in the default directory or update the paths in the script.