import os
import requests
import logging
from pathlib import Path
from PIL import Image
import vdf
import zlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NonSteamGameAdder:
    def __init__(self, game_exe_path, game_name, steam_user_data_path, steamgriddb_api_key, user_id, launch_options='', steam_dir=None):
        self.game_exe_path = game_exe_path
        self.game_name = game_name
        self.steam_user_data_path = steam_user_data_path
        self.steamgriddb_api_key = steamgriddb_api_key
        self.user_id = user_id
        self.launch_options = launch_options
        self.steam_dir = steam_dir or "C:\\Program Files (x86)\\Steam"  # Default for Windows, change for Linux if needed
        self.grid_folder = os.path.join(self.steam_user_data_path, self.user_id, "config", "grid")

        # Ensure the grid folder exists
        Path(self.grid_folder).mkdir(parents=True, exist_ok=True)

    def generate_appid(self, game_name, exe_path):
        """Generate a unique appid for the game based on its exe path and name."""
        unique_name = (exe_path + game_name).encode('utf-8')
        legacy_id = zlib.crc32(unique_name) | 0x80000000
        return str(legacy_id)

    def download_image(self, url, local_path, resize_to=None):
        """Download an image from URL and save it locally, optionally resizing."""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded image from {url} to {local_path}")

                # Resize the image if required
                if resize_to:
                    self.resize_image(local_path, resize_to)

                return True
            else:
                logger.error(f"Failed to download image: {url}, Status Code: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
        return False

    def resize_image(self, image_path, dimensions):
        """Resize an image to the specified dimensions."""
        try:
            with Image.open(image_path) as img:
                img = img.convert("RGBA").resize(dimensions, Image.Resampling.LANCZOS)
                img.save(image_path, format="PNG")
                logger.info(f"Resized image to {dimensions} and saved: {image_path}")
        except Exception as e:
            logger.error(f"Failed to resize image {image_path}: {e}")

    def fetch_steamgriddb_image(self, game_id, image_type):
        """Fetch a single image (first available) of specified type from SteamGridDB."""
        headers = {
            'Authorization': f'Bearer {self.steamgriddb_api_key}'
        }
        if image_type == 'hero':
            base_url = f'https://www.steamgriddb.com/api/v2/heroes/game/{game_id}'
        elif image_type == 'icon':
            base_url = f'https://www.steamgriddb.com/api/v2/icons/game/{game_id}'
        else:
            base_url = f'https://www.steamgriddb.com/api/v2/{image_type}s/game/{game_id}'

        response = requests.get(base_url, headers=headers)
        logger.info(f"Fetching {image_type} for game ID: {game_id}, URL: {base_url}, Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data['success'] and data['data']:
                return data['data'][0]['url']  # Return the URL of the first image found
        logger.error(f"Failed to fetch {image_type} for game ID: {game_id}")
        return None

    def save_images_to_grid(self, app_id, game_id):
        """Save grid, hero, logo, and icon images for the game to the correct Steam grid folder."""
        image_types = ['grid', 'hero', 'logo', 'icon']
        for image_type in image_types:
            url = self.fetch_steamgriddb_image(game_id, image_type)
            if url:
                extension = os.path.splitext(url)[1]
                image_path = os.path.join(self.grid_folder, f"{app_id}_{image_type}{extension}")
                if image_type == "icon":
                    self.download_image(url, image_path, resize_to=(64, 64))  # Resize icons
                else:
                    self.download_image(url, image_path)

    def add_non_steam_game(self):
        """Add a non-Steam game to the Steam shortcuts."""
        exe_path = self.game_exe_path
        game_name = self.game_name
        app_id = self.generate_appid(game_name, exe_path)
        game_path = os.path.dirname(exe_path)

        # Fetch images from SteamGridDB
        search_url = f'https://www.steamgriddb.com/api/v2/search/autocomplete/{game_name}'
        response = requests.get(search_url, headers={'Authorization': f'Bearer {self.steamgriddb_api_key}'})
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                game_id = data['data'][0]['id']  # Assuming first result is the best match
                self.save_images_to_grid(app_id, game_id)

        # Update Steam shortcut (VDF file)
        shortcuts_file = os.path.join(self.steam_user_data_path, self.user_id, 'config', 'shortcuts.vdf')
        try:
            if os.path.exists(shortcuts_file):
                with open(shortcuts_file, 'rb') as f:
                    shortcuts = vdf.binary_load(f)
            else:
                shortcuts = {'shortcuts': {}}

            new_entry = {
                "appid": app_id,
                "appname": game_name,
                "exe": f'"{exe_path}"',
                "StartDir": f'"{game_path}"',
                "LaunchOptions": self.launch_options,
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
            logger.info(f"Added game {game_name} to Steam shortcuts.")

        except Exception as e:
            logger.error(f"Failed to update shortcuts: {e}")

def select_steam_user():
    """Prompt the user to select a Steam account."""
    usernames = get_local_steam_usernames()  # This function should return a dictionary of user IDs and usernames
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

def main():
    """Main function to add a non-Steam game."""
    try:
        # Collect game details
        game_exe_path = input("Enter the path to your game\n> ").strip()
        game_name = input("Enter the name of the game\n> ").strip()
        launch_options = input("Enter any launch options or press Enter to skip\n> ").strip()

        # Validate the game path
        if not os.path.exists(game_exe_path):
            logger.error(f"Game path does not exist: {game_exe_path}")
            return

        # Select Steam user profile
        selected_user = select_steam_user()
        if not selected_user:
            logger.error("No valid user selected. Exiting.")
            return

        # Specify the SteamGridDB API key
        steamgriddb_api_key = input("Specify a SteamGridDB API key or press Enter to skip.\n> ").strip()

        # Add the non-Steam game using NonSteamGameAdder class
        game_adder = NonSteamGameAdder(game_exe_path, game_name, selected_user, steamgriddb_api_key, launch_options)
        game_adder.add_game()

    except Exception as e:
        logger.error(f"Unexpected error in main function: {e}")

# Allow the script to be imported as a module or run standalone
if __name__ == "__main__":
    main()