import os
import vdf
import logging
import requests
import zlib
from pathlib import Path
import platform

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Determine OS and set the correct Steam user data path
if platform.system() == "Windows":
    steam_user_data_path = os.path.join("C:\\Program Files (x86)\\Steam\\userdata")
elif platform.system() == "Linux":
    steam_user_data_path = os.path.expanduser("~/.steam/steam/userdata")
else:
    logger.error("Unsupported operating system.")
    exit(1)

# Define the grid folder for storing images
grid_folder = os.path.expanduser("~/.steam/grid_images")
Path(grid_folder).mkdir(parents=True, exist_ok=True)


def get_local_steam_usernames():
    """Get Steam usernames from local Steam files."""
    user_ids = [d for d in os.listdir(steam_user_data_path) if os.path.isdir(os.path.join(steam_user_data_path, d))]
    usernames = {}
    for user_id in user_ids:
        localconfig_path = os.path.join(steam_user_data_path, user_id, "config", "localconfig.vdf")
        if os.path.exists(localconfig_path):
            try:
                with open(localconfig_path, 'r') as f:
                    data = vdf.load(f)
                    username = data.get("UserLocalConfigStore", {}).get("friends", {}).get("PersonaName", "Unknown")
                    usernames[user_id] = username
            except Exception as e:
                logger.error(f"Failed to parse {localconfig_path}: {e}")
        else:
            usernames[user_id] = "Unknown"
    return usernames


def select_steam_user():
    """Prompt the user to select a Steam account."""
    usernames = get_local_steam_usernames()
    if not usernames:
        logger.error("No Steam users found.")
        return None

    print("Multiple Users Detected! Select a user:")
    for i, (user_id, username) in enumerate(usernames.items(), start=1):
        print(f"{i}. {username} ({user_id})")

    while True:
        try:
            selection = int(input("> "))
            if 1 <= selection <= len(usernames):
                selected_user_id = list(usernames.keys())[selection - 1]
                logger.info(f"Selected user: {usernames[selected_user_id]} ({selected_user_id})")
                return selected_user_id
        except ValueError:
            pass
        print("Invalid selection. Please enter a valid number.")


def fetch_steamgriddb_image(api_key, game_id, image_type):
    """Fetch a single image (first available) of specified type from SteamGridDB."""
    headers = {'Authorization': f'Bearer {api_key}'}
    url = f'https://www.steamgriddb.com/api/v2/{image_type}s/game/{game_id}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data['success'] and data['data']:
            return data['data'][0]['url']
    return None


def download_image(url, local_path):
    """Download an image from URL and save it locally."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Downloaded image from {url} to {local_path}")
            return True
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {e}")
    return False


def save_images(api_key, app_id, game_name):
    """Save grid, hero, and logo images for the game."""
    image_types = ['grid', 'hero', 'logo']
    for image_type in image_types:
        search_url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{game_name}"
        headers = {'Authorization': f'Bearer {api_key}'}
        response = requests.get(search_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                game_id = data['data'][0]['id']
                url = fetch_steamgriddb_image(api_key, game_id, image_type)
                if url:
                    extension = os.path.splitext(url)[1]
                    image_path = os.path.join(grid_folder, f'{app_id}_{image_type}{extension}')
                    download_image(url, image_path)


def add_non_steam_game():
    """Add a non-Steam game to the selected Steam account."""
    game_path = input("Enter the path to your game\n> ").strip()
    game_name = input("Enter the name of the game\n> ").strip()

    if not os.path.exists(game_path):
        logger.error(f"Game path does not exist: {game_path}")
        return

    user_id = select_steam_user()
    if not user_id:
        logger.error("No valid user selected. Exiting.")
        return

    api_key = input("Specify a SteamGridDB API key or press Enter to skip.\n> ").strip()
    app_id = generate_appid(game_name, game_path)

    # Generate or update shortcuts
    shortcuts_file = os.path.join(steam_user_data_path, user_id, "config", "shortcuts.vdf")
    try:
        if os.path.exists(shortcuts_file):
            with open(shortcuts_file, 'rb') as f:
                shortcuts = vdf.binary_load(f)
        else:
            shortcuts = {'shortcuts': {}}

        new_entry = {
            "appid": app_id,
            "appname": game_name,
            "exe": f'"{game_path}"',
            "StartDir": f'"{os.path.dirname(game_path)}"',
            "LaunchOptions": "",
            "IsHidden": 0,
            "AllowDesktopConfig": 1,
            "OpenVR": 0,
            "Devkit": 0,
            "DevkitGameID": "",
            "LastPlayTime": 0,
            "tags": {}
        }

        shortcuts['shortcuts'][str(len(shortcuts['shortcuts']))] = new_entry
        with open(shortcuts_file, 'wb') as f:
            vdf.binary_dump(shortcuts, f)
            logger.info(f"Added game '{game_name}' to Steam user {user_id}.")

        # Fetch and save images if API key is provided
        if api_key:
            save_images(api_key, app_id, game_name)

    except Exception as e:
        logger.error(f"Failed to update shortcuts: {e}")


def generate_appid(game_name, exe_path):
    """Generate a unique appid for the game based on its exe path and name."""
    unique_name = (exe_path + game_name).encode('utf-8')
    legacy_id = zlib.crc32(unique_name) | 0x80000000
    return str(legacy_id)


if __name__ == "__main__":
    add_non_steam_game()