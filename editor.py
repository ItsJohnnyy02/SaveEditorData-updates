import os
import json
import re
import string
import random
import urllib.request
import shutil
import tempfile
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Dict, List, Optional, Union
import subprocess
import requests

__version__ = "0.2.9"  # 

def check_for_updates():
    try:
        # Fetch the latest script from GitHub
        response = requests.get(GITHUB_RAW_URL, timeout=5)
        response.raise_for_status()  # Raise exception for bad status codes
        latest_code = response.text

        # Extract the version from the latest script
        for line in latest_code.splitlines():
            if line.startswith("__version__ ="):
                latest_version = line.split("=")[1].strip().strip('"')
                break
        else:
            raise ValueError("Version not found in GitHub script")

        # Compare versions
        if latest_version > __version__:
            # Ask user if they want to update (GUI popup)
            if messagebox.askyesno(
                "Update Available",
                f"A new version ({latest_version}) is available. Current version: {__version__}. Update now?"
            ):
                # Save the new script
                with open(CURRENT_SCRIPT, "w", encoding="utf-8") as f:
                    f.write(latest_code)
                logging.info(f"Updated script to version {latest_version}")

                # Restart the script
                os.execv(sys.executable, [sys.executable] + sys.argv)
                # os.execv replaces the current process, so no need to exit
        else:
            logging.debug("Script is up to date")

    except requests.RequestException as e:
        logging.error(f"Failed to check for updates: {str(e)}")
        messagebox.showwarning("Update Check Failed", f"Could not check for updates: {str(e)}")
    except Exception as e:
        logging.error(f"Update error: {str(e)}")
        messagebox.showerror("Update Error", f"Error during update: {str(e)}")

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class SaveManager:
    def __init__(self, save_path=""):
        self.current_save = Path(save_path) if save_path else None
        self.save_data: Dict[str, Union[dict, list]] = {}
        self.steamid_folder = None
        self.base_url = "https://github.com/ItsJohnnyy02/Schedule1SaveEditor/raw/main/Data/"
        check_for_updates()
        
    @staticmethod
    def _is_steamid_folder(name: str) -> bool:
        return re.fullmatch(r'[0-1][0-9]{16}', name) is not None

    def find_save_directory(self) -> Optional[Path]:
        base_path = Path.home() / "AppData" / "LocalLow" / "TVGS" / "Schedule I" / "saves"
        if not base_path.exists():
            return None
        steamid_folders = [f for f in base_path.iterdir() if f.is_dir() and self._is_steamid_folder(f.name)]
        if not steamid_folders:
            return None
        self.steamid_folder = steamid_folders[0]
        for item in self.steamid_folder.iterdir():
            if item.is_dir() and item.name.startswith("SaveGame_"):
                return item
        return None

    def get_save_organisation_name(self, save_path: Path) -> str:
        try:
            with open(save_path / "Game.json") as f:
                return json.load(f).get("OrganisationName", "Unknown Organization")
        except (FileNotFoundError, json.JSONDecodeError):
            return "Unknown Organization"

    def get_save_folders(self) -> List[Dict[str, str]]:
        if not hasattr(self, 'steamid_folder') or not self.steamid_folder:
            return []
        return [{"name": x.name, "path": str(x), "organisation_name": self.get_save_organisation_name(x)}
                for x in self.steamid_folder.iterdir()
                if x.is_dir() and re.fullmatch(r"SaveGame_[1-9]", x.name)]

    def load_save(self, save_path: Union[str, Path]) -> bool:
        self.current_save = Path(save_path)
        if not self.current_save.exists():
            logging.error(f"Save path does not exist: {save_path}")
            return False
        self.save_data = {}
        try:
            self.save_data["game"] = self._load_json_file("Game.json")
            self.save_data["money"] = self._load_json_file("Money.json")
            self.save_data["rank"] = self._load_json_file("Rank.json")
            self.save_data["time"] = self._load_json_file("Time.json")
            self.save_data["metadata"] = self._load_json_file("Metadata.json")
            self.save_data["properties"] = self._load_folder_data("Properties")
            self.save_data["vehicles"] = self._load_folder_data("OwnedVehicles")
            self.save_data["businesses"] = self._load_folder_data("Businesses")
            return True
        except Exception as e:
            logging.error(f"Error loading save: {e}")
            return False

    def _load_json_file(self, filename: str) -> dict:
        file_path = self.current_save / filename
        if not file_path.exists():
            return {}
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_folder_data(self, folder_name: str) -> list:
        folder_path = self.current_save / folder_name
        if not folder_path.exists():
            return []
        data = []
        for file in folder_path.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data.append(json.load(f))
            except json.JSONDecodeError:
                continue
        return data

    def _save_json_file(self, filename: str, data: dict):
        file_path = self.current_save / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def _download_and_extract_rar(self, rar_name: str, target_dir: Path) -> tuple[Path, None]:
        try:
            # Get the directory where editor.py is located
            editor_dir = Path(__file__).parent
            data_dir = editor_dir / "data"
            data_dir.mkdir(exist_ok=True)  # Create 'data' folder if it doesn't exist
            logging.debug(f"Using data directory: {data_dir}")

            rar_path = data_dir / rar_name
            extract_path = data_dir / "extracted"
            extract_path.mkdir(exist_ok=True)  # Create 'extracted' subfolder if it doesn't exist
            logging.debug(f"Extract path: {extract_path}")

            # Download the RAR file if it doesn’t already exist
            if not rar_path.exists():
                url = f"{self.base_url}{rar_name}"
                logging.debug(f"Downloading {url} to {rar_path}")
                urllib.request.urlretrieve(url, rar_path)
                if not rar_path.exists():
                    logging.error(f"RAR file not downloaded to {rar_path}")
                    raise RuntimeError(f"Failed to download {rar_name}. File not found at {rar_path}")
                logging.debug(f"Downloaded {rar_name} successfully")
            else:
                logging.debug(f"RAR file {rar_name} already exists at {rar_path}, skipping download")

                # Try 7-Zip first
                seven_zip_path = Path("C:/Program Files/7-Zip/7z.exe")
                extractor = None
                if seven_zip_path.exists():
                    extractor = "7zip"
                    logging.debug(f"Found 7-Zip at: {seven_zip_path}")
                else:
                    seven_zip_alt_path = Path("C:/Program Files (x86)/7-Zip/7z.exe")
                    if seven_zip_alt_path.exists():
                        seven_zip_path = seven_zip_alt_path
                        extractor = "7zip"
                        logging.debug(f"Found 7-Zip at alternative path: {seven_zip_path}")

                # If 7-Zip not found, try WinRAR
                if not extractor:
                    winrar_path = Path("C:/Program Files/WinRAR/WinRAR.exe")
                    if winrar_path.exists():
                        extractor = "winrar"
                        logging.debug(f"Found WinRAR at: {winrar_path}")
                    else:
                        winrar_alt_path = Path("C:/Program Files (x86)/WinRAR/WinRAR.exe")
                        if winrar_alt_path.exists():
                            winrar_path = winrar_alt_path
                            extractor = "winrar"
                            logging.debug(f"Found WinRAR at alternative path: {winrar_path}")

                # If neither is found, raise an error
                if not extractor:
                    raise FileNotFoundError(
                        "Neither 7-Zip nor WinRAR found. Please install one:\n"
                        "- 7-Zip: https://www.7-zip.org/ (default: C:/Program Files/7-Zip/7z.exe)\n"
                        "- WinRAR: https://www.win-rar.com/ (default: C:/Program Files/WinRAR/WinRAR.exe)"
                    )

                # Extract with the available tool
                if extractor == "7zip":
                    logging.debug(f"Extracting {rar_path} to {extract_path} with 7-Zip: {seven_zip_path}")
                    result = subprocess.run(
                        [str(seven_zip_path), "x", str(rar_path), f"-o{extract_path}", "-y"],
                        capture_output=True, text=True, check=True
                    )
                    logging.debug(f"7-Zip output: {result.stdout}")
                elif extractor == "winrar":
                    logging.debug(f"Extracting {rar_path} to {extract_path} with WinRAR: {winrar_path}")
                    result = subprocess.run(
                        [str(winrar_path), "x", "-y", str(rar_path), str(extract_path)],
                        capture_output=True, text=True, check=True
                    )
                    logging.debug(f"WinRAR output: {result.stdout}")

                # Check what was extracted
                extracted_contents = list(extract_path.iterdir())
                logging.debug(f"Contents of {extract_path}: {extracted_contents}")

                # Determine the correct extracted_dir
                extracted_dir = extract_path  # Default to extract_path
                expected_name = rar_name.replace('.rar', '').lower()
                for item in extracted_contents:
                    if item.is_dir() and item.name.lower() == expected_name:
                        extracted_dir = item
                        logging.debug(f"Found matching folder, using: {extracted_dir}")
                        break
                    elif item.is_dir() and item.name.lower() == "properties":  # Adjust if needed for other RARs
                        extracted_dir = item
                        logging.debug(f"Found 'properties' folder, using: {extracted_dir}")
                        break

                logging.debug(f"Final extracted_dir: {extracted_dir}")
                return extracted_dir, None  # No temp_dir to clean up

        except Exception as e:
            logging.error(f"Error in _download_and_extract_rar: {str(e)}")
            raise
    def get_save_info(self) -> dict:
        if not self.save_data:
            return {}
        creation_date = self.save_data.get("metadata", {}).get("CreationDate", {})
        formatted_date = (f"{creation_date.get('Year', 'Unknown')}-{creation_date.get('Month', 'Unknown'):02d}-"
                          f"{creation_date.get('Day', 'Unknown'):02d} {creation_date.get('Hour', 'Unknown'):02d}:"
                          f"{creation_date.get('Minute', 'Unknown'):02d}:{creation_date.get('Second', 'Unknown'):02d}")
        money_data = self.save_data.get("money", {})
        rank_data = self.save_data.get("rank", {})
        time_data = self.save_data.get("time", {})
        return {
            "game_version": self.save_data.get("game", {}).get("GameVersion", "Unknown"),
            "creation_date": formatted_date if creation_date else "Unknown",
            "organisation_name": self.save_data.get("game", {}).get("OrganisationName", "Unknown"),
            "online_money": int(money_data.get("OnlineBalance", 0)),
            "networth": int(money_data.get("Networth", 0)),
            "lifetime_earnings": int(money_data.get("LifetimeEarnings", 0)),
            "weekly_deposit_sum": int(money_data.get("WeeklyDepositSum", 0)),
            "current_rank": rank_data.get("CurrentRank", "Unknown"),
            "rank_number": int(rank_data.get("Rank", 0)),
            "tier": int(rank_data.get("Tier", 0)),
            "play_time_seconds": int(time_data.get("Playtime", 0))
        }

    def set_value(self, file_name: str, key: str, value):
        if file_name in self.save_data:
            self.save_data[file_name][key] = value
            self._save_json_file(f"{file_name}.json", self.save_data[file_name])

    def complete_all_quests(self) -> tuple[int, int]:
        if not self.current_save:
            logging.error("No save loaded")
            return 0, 0

        quests_path = self.current_save / "Quests"
        if not quests_path.exists():
            try:
                extracted_dir = self._download_and_extract_rar("Quests.rar", quests_path)
                shutil.copytree(extracted_dir, quests_path, dirs_exist_ok=True)
                logging.debug(f"Extracted Quests.rar to {quests_path}")
            except Exception as e:
                logging.error(f"Failed to extract Quests.rar: {str(e)}")
                return 0, 0

        quests_completed = 0
        objectives_completed = 0

        for file_path in quests_path.glob("*.json"):
            try:
                rel_path = file_path.relative_to(self.current_save)
                data = self._load_json_file(str(rel_path))
                
                if data.get("DataType") != "QuestData":
                    logging.debug(f"Skipping non-quest file: {file_path}")
                    continue

                modified = False
                current_state = data.get("State")
                if current_state in (0, 1):
                    data["State"] = 2
                    quests_completed += 1
                    modified = True

                if "Entries" in data and isinstance(data["Entries"], list):
                    for entry in data["Entries"]:
                        current_entry_state = entry.get("State")
                        if current_entry_state in (0, 1):
                            entry["State"] = 2
                            objectives_completed += 1
                            modified = True

                if modified:
                    self._save_json_file(str(rel_path), data)

            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")
                continue

        logging.debug(f"Completed {quests_completed} quests, {objectives_completed} objectives")
        return quests_completed, objectives_completed

    def unlock_all_properties(self) -> int:
        if not self.current_save:
            raise ValueError("No save loaded")

        properties_path = self.current_save / "Properties"
        properties_path.mkdir(parents=True, exist_ok=True)
        logging.debug(f"Target properties path: {properties_path}")

        temp_dir = None
        try:
            extracted_dir, temp_dir = self._download_and_extract_rar("Properties.rar", properties_path)
            logging.debug(f"Extracted_dir returned: {extracted_dir}")
            logging.debug(f"Contents of extracted_dir: {list(extracted_dir.iterdir())}")

            for prop_type in extracted_dir.iterdir():
                if prop_type.is_dir():
                    dst_dir = properties_path / prop_type.name
                    logging.debug(f"Copying {prop_type} to {dst_dir}")
                    if not dst_dir.exists():
                        shutil.copytree(prop_type, dst_dir)
                        logging.debug(f"Successfully copied {prop_type} to {dst_dir}")
                    else:
                        logging.debug(f"Destination {dst_dir} already exists, skipping copy")

            updated = 0
            missing_template = {
                "DataType": "PropertyData",
                "DataVersion": 0,
                "GameVersion": "0.2.9f4",
                "PropertyCode": "",
                "IsOwned": True,
                "SwitchStates": [True, True, True, True],
                "ToggleableStates": [True, True]
            }
        
            for prop_type in properties_path.iterdir():
                if prop_type.is_dir():
                    json_path = prop_type / "Property.json"
                    logging.debug(f"Processing property at {json_path}")
                    if not json_path.exists():
                        template = missing_template.copy()
                        template["PropertyCode"] = prop_type.name.lower()
                        self._save_json_file(json_path.relative_to(self.current_save), template)
                        updated += 1
                        logging.debug(f"Created new property file at {json_path}")
                    else:
                        data = self._load_json_file(json_path.relative_to(self.current_save))
                        data["IsOwned"] = True
                        for key in missing_template:
                            if key not in data:
                                data[key] = missing_template[key]
                        data["SwitchStates"] = [True, True, True, True]
                        data["ToggleableStates"] = [True, True]
                        self._save_json_file(json_path.relative_to(self.current_save), data)
                        updated += 1
                        logging.debug(f"Updated existing property file at {json_path}")
        
            return updated

        except Exception as e:
            logging.error(f"Failed to unlock properties: {str(e)}")
            raise RuntimeError(f"Failed to unlock properties: {str(e)}")
        finally:
            if temp_dir:
                temp_dir.cleanup()
                logging.debug(f"Cleaned up temp directory in unlock_all_properties")

    def unlock_all_businesses(self) -> int:
        if not self.current_save:
            raise ValueError("No save loaded")

        businesses_path = self.current_save / "Businesses"
        businesses_path.mkdir(parents=True, exist_ok=True)
        temp_dir = None

        try:
            extracted_dir, temp_dir = self._download_and_extract_rar("Businesses.rar", businesses_path)
            for bus_type in extracted_dir.iterdir():
                if bus_type.is_dir():
                    dst_dir = businesses_path / bus_type.name
                    if not dst_dir.exists():
                        shutil.copytree(bus_type, dst_dir)

            updated = 0
            missing_template = {
                "DataType": "BusinessData",
                "DataVersion": 0,
                "GameVersion": "0.2.9f4",
                "PropertyCode": "",
                "IsOwned": True,
                "SwitchStates": [True, True, True, True],
                "ToggleableStates": [True, True]
            }
        
            for bus_type in businesses_path.iterdir():
                if bus_type.is_dir():
                    json_path = bus_type / "Business.json"
                    if not json_path.exists():
                        template = missing_template.copy()
                        template["PropertyCode"] = bus_type.name.lower()
                        self._save_json_file(json_path.relative_to(self.current_save), template)
                        updated += 1
                    else:
                        data = self._load_json_file(json_path.relative_to(self.current_save))
                        data["IsOwned"] = True
                        for key in missing_template:
                            if key not in data:
                                data[key] = missing_template[key]
                        data["SwitchStates"] = [True, True, True, True]
                        data["ToggleableStates"] = [True, True]
                        self._save_json_file(json_path.relative_to(self.current_save), data)
                        updated += 1
        
            return updated
        except Exception as e:
            raise RuntimeError(f"Failed to unlock businesses: {str(e)}")
        finally:
            if temp_dir:
                temp_dir.cleanup()
                logging.debug(f"Cleaned up temp directory in unlock_all_businesses")

    def update_npc_relationships(self) -> int:
        if not self.current_save:
            raise ValueError("No save loaded")

        npcs_dir = self.current_save / "NPCs"
        npcs_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = None

        try:
            extracted_dir, temp_dir = self._download_and_extract_rar("NPCs.rar", npcs_dir)
            existing_npcs = {npc.name for npc in npcs_dir.iterdir() if npc.is_dir()}
            for npc_template in extracted_dir.iterdir():
                if npc_template.is_dir() and npc_template.name not in existing_npcs:
                    shutil.copytree(npc_template, npcs_dir / npc_template.name)

            updated_count = 0
            for npc_folder in npcs_dir.iterdir():
                if not npc_folder.is_dir():
                    continue

                relationship_file = npc_folder / "Relationship.json"
                if relationship_file.exists():
                    rel_data = self._load_json_file(relationship_file.relative_to(self.current_save))
                    rel_data.update({
                        "RelationDelta": 999,
                        "Unlocked": True,
                        "UnlockType": 1
                    })
                    self._save_json_file(relationship_file.relative_to(self.current_save), rel_data)
                    updated_count += 1

                npc_file = npc_folder / "NPC.json"
                if npc_file.exists():
                    npc_data = self._load_json_file(npc_file.relative_to(self.current_save))
                    if npc_data.get("DataType") == "DealerData":
                        npc_data["Recruited"] = True
                        self._save_json_file(npc_file.relative_to(self.current_save), npc_data)

            return updated_count
        except Exception as e:
            raise RuntimeError(f"NPC relationship update failed: {str(e)}")
        finally:
            if temp_dir:
                temp_dir.cleanup()
                logging.debug(f"Cleaned up temp directory in update_npc_relationships")

    def unlock_all_items_weeds(self) -> int:
        if not self.current_save:
            raise ValueError("No save loaded")

        # Set rank to maximum to ensure all items are accessible
        try:
            data = self._load_json_file("Rank.json")
            data["Rank"] = 999
            data["Tier"] = 999
            self._save_json_file("Rank.json", data)
        except Exception as e:
            logging.error(f"Failed to update Rank.json: {str(e)}")
            raise RuntimeError(f"Failed to update rank: {str(e)}")

        products_path = self.current_save / "Products"
        products_path.mkdir(parents=True, exist_ok=True)
        temp_dir = None

        try:
            # Download and extract Products.rar
            extracted_dir, temp_dir = self._download_and_extract_rar("Products.rar", products_path)
            logging.debug(f"Extracted_dir for Products: {extracted_dir}")
            logging.debug(f"Contents of extracted_dir: {list(extracted_dir.iterdir())}")

            # Copy extracted contents to the Products folder
            shutil.copytree(extracted_dir, products_path, dirs_exist_ok=True)
            logging.debug(f"Copied contents to {products_path}")

            # Template for product data
            product_template = {
                "DataType": "ProductData",
                "DataVersion": 0,
                "GameVersion": "0.2.9f4",
                "ProductCode": "",
                "IsUnlocked": True,  # Ensure all products are unlocked
                "Quantity": 9999     # Optional: Set a high quantity
            }

            updated = 0
            # Process each product folder
            for product_dir in products_path.iterdir():
                if product_dir.is_dir():
                    json_path = product_dir / "Product.json"
                    logging.debug(f"Processing product at {json_path}")
                    if not json_path.exists():
                        # Create a new product file if it doesn’t exist
                        template = product_template.copy()
                        template["ProductCode"] = product_dir.name.lower()
                        self._save_json_file(json_path.relative_to(self.current_save), template)
                        updated += 1
                        logging.debug(f"Created new product file at {json_path}")
                    else:
                        # Update existing product file
                        data = self._load_json_file(json_path.relative_to(self.current_save))
                        data["IsUnlocked"] = True
                        data["Quantity"] = 9999  # Optional: Ensure ample stock
                        for key in product_template:
                            if key not in data:
                                data[key] = product_template[key]
                        self._save_json_file(json_path.relative_to(self.current_save), data)
                        updated += 1
                        logging.debug(f"Updated existing product file at {json_path}")

            return updated

        except Exception as e:
            logging.error(f"Failed to unlock items and weeds: {str(e)}")
            raise RuntimeError(f"Failed to unlock items and weeds: {str(e)}")
        finally:
            if temp_dir:
                temp_dir.cleanup()
                logging.debug(f"Cleaned up temp directory in unlock_all_items_weeds")

    def recruit_all_dealers(self) -> int:
        if not self.current_save:
            raise ValueError("No save loaded")
        
        npcs_dir = self.current_save / "NPCs"
        if not npcs_dir.exists():
            self.update_npc_relationships()
        
        updated_count = 0
        for npc_folder in npcs_dir.iterdir():
            if npc_folder.is_dir():
                npc_json_path = npc_folder / "NPC.json"
                if npc_json_path.exists():
                    try:
                        with open(npc_json_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        if data.get("DataType") == "DealerData" and "Recruited" in data:
                            data["Recruited"] = True
                            with open(npc_json_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, indent=4)
                            updated_count += 1
                    except json.JSONDecodeError:
                        continue
        return updated_count

    def modify_variables(self) -> int:
        if not self.current_save:
            raise ValueError("No save loaded")

        variables_dir = self.current_save / "Variables"
        if not variables_dir.exists():
            try:
                extracted_dir = self._download_and_extract_rar("Variables.rar", variables_dir)
                shutil.copytree(extracted_dir, variables_dir, dirs_exist_ok=True)
            except Exception as e:
                logging.error(f"Failed to extract Variables.rar: {str(e)}")

        count = 0
        for json_file in variables_dir.glob("*.json"):
            rel_path = json_file.relative_to(self.current_save)
            data = self._load_json_file(str(rel_path))
            
            if "Value" in data:
                original = data["Value"]
                if data["Value"] == "False":
                    data["Value"] = "True"
                    count += 1
                elif data["Value"] not in ["True", "False"]:
                    data["Value"] = "999999999"
                    count += 1
                
                if data["Value"] != original:
                    self._save_json_file(str(rel_path), data)

        return count

    def update_world_storage_entities(self) -> int:
        if not self.current_save:
            raise ValueError("No save loaded")

        storage_path = self.current_save / "WorldStorageEntities"
        storage_path.mkdir(parents=True, exist_ok=True)
        temp_dir = None

        try:
            # Download and extract WorldStorageEntities.rar
            extracted_dir, temp_dir = self._download_and_extract_rar("WorldStorageEntities.rar", storage_path)
            logging.debug(f"Extracted_dir for WorldStorageEntities: {extracted_dir}")
            logging.debug(f"Contents of extracted_dir: {list(extracted_dir.iterdir())}")

            # Copy extracted contents to the WorldStorageEntities folder
            shutil.copytree(extracted_dir, storage_path, dirs_exist_ok=True)
            logging.debug(f"Copied contents to {storage_path}")

            # Template for storage entity data
            storage_template = {
                "DataType": "StorageEntityData",
                "DataVersion": 0,
                "GameVersion": "0.2.9f4",
                "EntityCode": "",
                "IsUnlocked": True,  # Ensure all storage entities are accessible
                "Capacity": 9999     # Optional: Set a high capacity
            }

            updated = 0
            # Process each storage JSON file directly (assuming flat structure)
            for json_file in storage_path.glob("*.json"):
                rel_path = json_file.relative_to(self.current_save)
                logging.debug(f"Processing storage file at {json_file}")
                data = self._load_json_file(str(rel_path))
                if not data:  # If file is empty or invalid, create new
                    template = storage_template.copy()
                    template["EntityCode"] = json_file.stem.lower()
                    self._save_json_file(str(rel_path), template)
                    updated += 1
                    logging.debug(f"Created new storage file at {json_file}")
                else:
                    # Update existing storage file
                    data["IsUnlocked"] = True
                    data["Capacity"] = 9999  # Optional: Ensure high capacity
                    for key in storage_template:
                        if key not in data:
                            data[key] = storage_template[key]
                    self._save_json_file(str(rel_path), data)
                    updated += 1
                    logging.debug(f"Updated existing storage file at {json_file}")

            return updated

        except Exception as e:
            logging.error(f"Failed to update world storage entities: {str(e)}")
            raise RuntimeError(f"Failed to update world storage entities: {str(e)}")
        finally:
            if temp_dir:
                temp_dir.cleanup()
                logging.debug(f"Cleaned up temp directory in update_world_storage_entities")

class SaveEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Schedule I Save Editor")
        self.root.geometry("1000x725")
        self.root.configure(bg="#212121")
        self.manager = SaveManager()
        self.folder_path = ""

        self.main_frame = tk.Frame(root, bg="#212121")
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.header_frame = tk.Frame(self.main_frame, bg="#263238")
        self.header_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(self.header_frame, text="Schedule I Save Editor", 
                 font=("Helvetica", 14, "bold"), foreground="#ffffff", 
                 background="#263238").pack(side="left", padx=10, pady=5)
        
        self.folder_label = ttk.Label(self.header_frame, text="No save loaded", 
                                    foreground="#b0bec5", background="#263238")
        self.folder_label.pack(side="right", padx=10)

        self.control_frame = tk.Frame(self.main_frame, bg="#212121")
        self.control_frame.pack(fill="x", pady=(0, 10))
        
        self.folder_btn = ttk.Button(self.control_frame, text="Load Save Folder", 
                                   command=self.select_folder, style="Accent.TButton")
        self.folder_btn.pack(side="left", padx=(0, 5))
        
        self.default_btn = ttk.Button(self.control_frame, text="Load Default Path", 
                                    command=self.load_default_path, style="Accent.TButton")
        self.default_btn.pack(side="left")

        self.content_frame = tk.Frame(self.main_frame, bg="#212121")
        self.content_frame.pack(fill="both", expand=True)
        
        self.tab_widget = ttk.Notebook(self.content_frame)
        self.tab_widget.pack(fill="both", expand=True, pady=5)

        self.money_tab = tk.Frame(self.tab_widget, bg="#212121")
        self.tab_widget.add(self.money_tab, text="Money")
        self.money_entries = self.create_form_section(self.money_tab, "Financial Data", [
            ("Cash", "Current available cash"),
            ("Wealth", "Total net worth"),
            ("Earnings", "Lifetime earnings"),
            ("Weekly Income", "Weekly revenue")
        ])

        self.rank_tab = tk.Frame(self.tab_widget, bg="#212121")
        self.tab_widget.add(self.rank_tab, text="Rank")
        self.rank_entries = self.create_form_section(self.rank_tab, "Progression", [
            ("Level", "Current rank level"),
            ("Sub-Level", "Tier within rank"),
            ("Experience", "Current experience points"),
            ("Total Exp", "Total accumulated XP")
        ])

        self.players_tab = tk.Frame(self.tab_widget, bg="#212121")
        self.tab_widget.add(self.players_tab, text="Players")
        self.setup_players_tab()

        self.variables_tab = tk.Frame(self.tab_widget, bg="#212121")
        self.tab_widget.add(self.variables_tab, text="Variables")
        self.setup_variables_tab()

        self.misc_tab = tk.Frame(self.tab_widget, bg="#212121")
        self.tab_widget.add(self.misc_tab, text="Miscellaneous")
        self.misc_entries = self.create_form_section(self.misc_tab, "Game Settings", [
            ("Gang Name", "Organization name"),
            ("Time Played", "Total play time (seconds)"),
            ("Law Pressure", "Current law enforcement intensity")
        ])

        self.cheats_tab = tk.Frame(self.tab_widget, bg="#212121")
        self.tab_widget.add(self.cheats_tab, text="Cheats")
        self.setup_cheats_tab()

        self.footer_frame = tk.Frame(self.main_frame, bg="#212121")
        self.footer_frame.pack(fill="x", pady=(10, 0))
        
        self.status = ttk.Label(self.footer_frame, text="Ready", foreground="#b0bec5", 
                              background="#212121", font=("Helvetica", 9))
        self.status.pack(side="left", padx=5)
        
        self.save_btn = ttk.Button(self.footer_frame, text="Apply Changes", 
                                 command=self.save_changes, state="disabled", 
                                 style="Accent.TButton")
        self.save_btn.pack(side="right", padx=5)

        self.apply_professional_theme()
        self.auto_load_default_save()

    def apply_professional_theme(self):
        style = ttk.Style()
        style.theme_use("default")
        
        style.configure("TNotebook", background="#212121", borderwidth=0)
        style.configure("TNotebook.Tab", background="#37474f", foreground="#ffffff",
                       padding=[12, 6], font=("Helvetica", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", 
                 background=[("selected", "#455a64"), ("active", "#546e7a")],
                 foreground=[("selected", "#ffffff")])
        
        style.configure("TButton", background="#37474f", foreground="#ffffff",
                       font=("Helvetica", 9), padding=6, borderwidth=1)
        style.map("TButton", 
                 background=[("active", "#546e7a")],
                 foreground=[("disabled", "#78909c")])
        
        style.configure("Accent.TButton", background="#0288d1", foreground="#ffffff")
        style.map("Accent.TButton",
                 background=[("active", "#0277bd"), ("disabled", "#4fc3f7")])
        
        style.configure("TLabel", background="#212121", foreground="#ffffff",
                       font=("Helvetica", 9))
        style.configure("TEntry", fieldbackground="#37474f", foreground="#ffffff",
                       insertcolor="#ffffff", borderwidth=1)

    def create_form_section(self, tab, title, fields):
        entries = {}
        container = ttk.LabelFrame(tab, text=title, padding=10)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        for i, (label, tooltip) in enumerate(fields):
            ttk.Label(container, text=f"{label}:", font=("Helvetica", 9)).grid(
                row=i, column=0, padx=5, pady=5, sticky="e")
            entry = ttk.Entry(container, width=35, font=("Helvetica", 9))
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            entries[label] = entry
        container.grid_columnconfigure(1, weight=1)
        return entries

    def setup_players_tab(self):
        container = ttk.LabelFrame(self.players_tab, text="Player Data", padding=10)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        select_frame = tk.Frame(container, bg="#212121")
        select_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(select_frame, text="Select Player:", font=("Helvetica", 9)).pack(
            side="left", padx=5)
        self.players_dropdown = ttk.Combobox(select_frame, state="readonly", width=35,
                                          font=("Helvetica", 9))
        self.players_dropdown.pack(side="left", padx=5)
        self.players_dropdown.bind("<<ComboboxSelected>>", self.load_player_data)

        text_frame = tk.Frame(container, bg="#212121")
        text_frame.pack(fill="both", expand=True)
        
        self.player_data_text = tk.Text(text_frame, wrap="none", bg="#37474f", fg="#ffffff",
                                      font=("Consolas", 10), height=15, borderwidth=1,
                                      relief="flat")
        scroll_y = ttk.Scrollbar(text_frame, orient="vertical", 
                               command=self.player_data_text.yview)
        scroll_x = ttk.Scrollbar(text_frame, orient="horizontal", 
                               command=self.player_data_text.xview)
        self.player_data_text.configure(yscrollcommand=scroll_y.set, 
                                      xscrollcommand=scroll_x.set)
        
        self.player_data_text.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        btn_frame = tk.Frame(container, bg="#212121")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(btn_frame, text="Save Player", command=self.save_player_data,
                  style="Accent.TButton").pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Refresh List", command=self.load_players,
                  style="Accent.TButton").pack(side="left")

    def setup_variables_tab(self):
        container = ttk.LabelFrame(self.variables_tab, text="Variables Data", padding=10)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        select_frame = tk.Frame(container, bg="#212121")
        select_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(select_frame, text="Select Variable:", font=("Helvetica", 9)).pack(
            side="left", padx=5)
        self.variables_dropdown = ttk.Combobox(select_frame, state="readonly", width=35,
                                             font=("Helvetica", 9))
        self.variables_dropdown.pack(side="left", padx=5)
        self.variables_dropdown.bind("<<ComboboxSelected>>", self.load_variable_data)

        text_frame = tk.Frame(container, bg="#212121")
        text_frame.pack(fill="both", expand=True)
        
        self.variable_data_text = tk.Text(text_frame, wrap="none", bg="#37474f", fg="#ffffff",
                                        font=("Consolas", 10), height=15, borderwidth=1,
                                        relief="flat")
        scroll_y = ttk.Scrollbar(text_frame, orient="vertical", 
                               command=self.variable_data_text.yview)
        scroll_x = ttk.Scrollbar(text_frame, orient="horizontal", 
                               command=self.variable_data_text.xview)
        self.variable_data_text.configure(yscrollcommand=scroll_y.set, 
                                        xscrollcommand=scroll_x.set)
        
        self.variable_data_text.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        btn_frame = tk.Frame(container, bg="#212121")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(btn_frame, text="Save Variable", command=self.save_variable_data,
                  style="Accent.TButton").pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Refresh List", command=self.load_variables,
                  style="Accent.TButton").pack(side="left", padx=(5, 5))
        
        ttk.Button(btn_frame, text="Modify Variables", command=self.modify_variables,
                  style="Accent.TButton").pack(side="left", padx=5)

    def setup_cheats_tab(self):
        container = ttk.LabelFrame(self.cheats_tab, text="Cheat Options", padding=10)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(container, bg="#212121")
        btn_frame.pack(fill="x", pady=5)
        
        ttk.Button(btn_frame, text="Unlock All Properties", command=self.unlock_all_properties,
                  style="Accent.TButton").pack(side="left", padx=(35, 5))
        ttk.Button(btn_frame, text="Unlock All Businesses", command=self.unlock_all_businesses,
                  style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Unlock All Items/Weeds", command=self.unlock_all_items_weeds,
                  style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Recruit All Dealers", command=self.recruit_all_dealers,
                  style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Complete All Quests", command=self.complete_all_quests,
                  style="Accent.TButton").pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Update World Storage", command=self.update_world_storage_entities,
                  style="Accent.TButton").pack(side="left", padx=5)

    def get_save_folders(self):
        base_path = Path(os.getenv('LOCALAPPDATA', 'C:\\Users\\Public\\AppData\\Local')) / '..' / 'LocalLow' / 'TVGS' / 'Schedule I' / 'Saves'
        save_folders = []
        
        logging.debug(f"Searching for saves in base path: {base_path}")
        self.status.config(text=f"Searching: {base_path}")

        if not base_path.exists():
            logging.error(f"Base path does not exist: {base_path}")
            self.status.config(text=f"Path not found: {base_path}")
            return save_folders

        try:
            for steam_id in os.listdir(base_path):
                steam_id_path = base_path / steam_id
                if not steam_id_path.is_dir() or not steam_id.isdigit():
                    continue
                
                for folder in os.listdir(steam_id_path):
                    if not folder.startswith("SaveGame_"):
                        continue
                    
                    save_path = steam_id_path / folder
                    if not save_path.is_dir():
                        continue
                    
                    players_path = save_path / "Players"
                    if not players_path.exists():
                        continue
                    
                    org_name = "Unknown"
                    game_json = save_path / "Game.json"
                    if game_json.exists():
                        with open(game_json, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            org_name = data.get("OrganisationName", "Unknown")
                    
                    save_folders.append({
                        'path': str(save_path),
                        'name': folder,
                        'organisation_name': org_name,
                        'modified_time': os.path.getmtime(save_path)
                    })
                    
            if not save_folders:
                self.status.config(text="No valid saves found")
            else:
                self.status.config(text=f"Found {len(save_folders)} saves")
                
        except Exception as e:
            logging.error(f"Error searching for saves: {str(e)}")
            self.status.config(text=f"Search error: {str(e)}")
        
        return sorted(save_folders, key=lambda x: x['modified_time'], reverse=True)

    def auto_load_default_save(self):
        save_folders = self.get_save_folders()
        
        if save_folders:
            most_recent_save = save_folders[0]
            self.folder_path = most_recent_save['path']
            if self.manager.load_save(self.folder_path):
                self.folder_label.config(text=f"Loaded: {most_recent_save['name']} ({most_recent_save['organisation_name']})")
                self.save_btn.config(state="normal")
                self.load_players()
                self.load_variables()
                self.load_current_values()
                self.status.config(text=f"Auto-loaded: {most_recent_save['name']}")
            else:
                self.status.config(text="Failed to auto-load save")

    def load_default_path(self):
        save_folders = self.get_save_folders()
        
        if save_folders:
            most_recent_save = save_folders[0]
            self.folder_path = most_recent_save['path']
            if self.manager.load_save(self.folder_path):
                self.folder_label.config(text=f"Loaded: {most_recent_save['name']} ({most_recent_save['organisation_name']})")
                self.save_btn.config(state="normal")
                self.load_players()
                self.load_variables()
                self.load_current_values()
                self.status.config(text=f"Loaded: {most_recent_save['name']}")
            else:
                self.status.config(text="Failed to load default save")
        else:
            messagebox.showinfo("Info", "No valid save folders found")

    def select_folder(self):
        initial_dir = Path(os.getenv('LOCALAPPDATA', 'C:\\Users\\Public\\AppData\\Local')) / '..' / 'LocalLow' / 'TVGS' / 'Schedule I' / 'Saves'
        if not initial_dir.exists():
            initial_dir = Path.home()
            
        self.folder_path = filedialog.askdirectory(title="Select Schedule I Save Folder", 
                                                 initialdir=str(initial_dir))
        
        if self.folder_path:
            if self.manager.load_save(self.folder_path):
                org_name = self.manager.get_save_info().get("organisation_name", "Unknown")
                self.folder_label.config(text=f"Loaded: {os.path.basename(self.folder_path)} ({org_name})")
                self.save_btn.config(state="normal")
                self.load_players()
                self.load_variables()
                self.load_current_values()
                self.status.config(text="Save folder loaded successfully")
            else:
                messagebox.showerror("Error", "Failed to load selected save folder!")
                self.status.config(text="Invalid folder selected")

    def load_players(self):
        players_folder = Path(self.folder_path) / "Players"
        if not players_folder.exists():
            self.players_dropdown["values"] = []
            self.player_data_text.delete("1.0", tk.END)
            self.player_data_text.insert(tk.END, "Players folder not found")
            self.status.config(text="Players folder not found")
            return

        player_folders = [f for f in os.listdir(players_folder) 
                         if os.path.isdir(os.path.join(players_folder, f)) and f.startswith("Player_")]
        
        if player_folders:
            self.players_dropdown["values"] = sorted(player_folders)
            self.players_dropdown.set(player_folders[0])
            self.load_player_data()
            self.status.config(text=f"Loaded {len(player_folders)} player folders")
        else:
            self.players_dropdown["values"] = []
            self.player_data_text.delete("1.0", tk.END)
            self.player_data_text.insert(tk.END, "No player folders found")
            self.status.config(text="No player folders found")

    def load_player_data(self, event=None):
        selected_player = self.players_dropdown.get()
        if not selected_player:
            self.player_data_text.delete("1.0", tk.END)
            self.player_data_text.insert(tk.END, "No player selected")
            self.status.config(text="No player selected")
            return

        player_folder = Path(self.folder_path) / "Players" / selected_player
        combined_data = {}
        json_files = [f for f in os.listdir(player_folder) if f.lower().endswith('.json')]
        for json_file in json_files:
            file_path = player_folder / json_file
            with open(file_path, "r", encoding='utf-8') as f:
                data = json.load(f)
                combined_data[os.path.splitext(json_file)[0]] = data
        self.player_data_text.delete("1.0", tk.END)
        self.player_data_text.insert(tk.END, json.dumps(combined_data, indent=2))
        self.status.config(text=f"Loaded player: {selected_player}")

    def save_player_data(self):
        selected_player = self.players_dropdown.get()
        if not selected_player:
            messagebox.showwarning("Warning", "No player selected!")
            return
        player_folder = Path(self.folder_path) / "Players" / selected_player
        try:
            combined_data = json.loads(self.player_data_text.get("1.0", tk.END))
            for key, data in combined_data.items():
                file_path = player_folder / f"{key}.json"
                with open(file_path, "w", encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            self.status.config(text=f"Saved player: {selected_player}")
            messagebox.showinfo("Success", "Player data saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save player data: {str(e)}")
            self.status.config(text="Error saving player data")

    def load_variables(self):
        variables_folder = Path(self.folder_path) / "Variables"
        if not variables_folder.exists():
            self.variables_dropdown["values"] = []
            self.variable_data_text.delete("1.0", tk.END)
            self.variable_data_text.insert(tk.END, "Variables folder not found")
            self.status.config(text="Variables folder not found")
            return

        variable_files = [f for f in os.listdir(variables_folder) if f.lower().endswith(".json")]
        
        if variable_files:
            self.variables_dropdown["values"] = sorted(variable_files)
            self.variables_dropdown.set(variable_files[0])
            self.load_variable_data()
            self.status.config(text=f"Loaded {len(variable_files)} variable files")
        else:
            self.variables_dropdown["values"] = []
            self.variable_data_text.delete("1.0", tk.END)
            self.variable_data_text.insert(tk.END, "No variable files found")
            self.status.config(text="No variable files found")

    def load_variable_data(self, event=None):
        selected_variable = self.variables_dropdown.get()
        if not selected_variable:
            self.variable_data_text.delete("1.0", tk.END)
            self.variable_data_text.insert(tk.END, "No variable selected")
            self.status.config(text="No variable selected")
            return

        file_path = Path(self.folder_path) / "Variables" / selected_variable
        with open(file_path, "r", encoding='utf-8') as f:
            variable_data = json.load(f)
        self.variable_data_text.delete("1.0", tk.END)
        self.variable_data_text.insert(tk.END, json.dumps(variable_data, indent=2))
        self.status.config(text=f"Loaded variable: {selected_variable}")

    def save_variable_data(self):
        selected_variable = self.variables_dropdown.get()
        if not selected_variable:
            messagebox.showwarning("Warning", "No variable selected!")
            return
        file_path = Path(self.folder_path) / "Variables" / selected_variable
        try:
            variable_data = json.loads(self.variable_data_text.get("1.0", tk.END))
            with open(file_path, "w", encoding='utf-8') as f:
                json.dump(variable_data, f, indent=2)
            self.status.config(text=f"Saved variable: {selected_variable}")
            messagebox.showinfo("Success", "Variable data saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save variable data: {str(e)}")
            self.status.config(text="Error saving variable data")

    def complete_all_quests(self):
        if not self.manager.current_save:
            messagebox.showwarning("Warning", "No save loaded!")
            self.status.config(text="No save loaded")
            return

        try:
            quests_completed, objectives_completed = self.manager.complete_all_quests()
            message = f"Completed {quests_completed} quests"
            if objectives_completed > 0:
                message += f" and {objectives_completed} objectives"
            
            self.status.config(text=message)
            if quests_completed > 0 or objectives_completed > 0:
                messagebox.showinfo("Success", f"{message} successfully!")
            else:
                messagebox.showinfo("Info", "No quests found or all already completed in Quests folder")
            self.load_variables()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to complete quests: {str(e)}")
            self.status.config(text="Error completing quests")

    def unlock_all_properties(self):
        if not self.manager.current_save:
            messagebox.showwarning("Warning", "No save loaded!")
            self.status.config(text="No save loaded")
            return
        try:
            count = self.manager.unlock_all_properties()
            self.status.config(text=f"Unlocked {count} properties")
            messagebox.showinfo("Success", f"Unlocked {count} properties successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unlock properties: {str(e)}")
            self.status.config(text="Error unlocking properties")

    def unlock_all_businesses(self):
        if not self.manager.current_save:
            messagebox.showwarning("Warning", "No save loaded!")
            self.status.config(text="No save loaded")
            return
        try:
            count = self.manager.unlock_all_businesses()
            self.status.config(text=f"Unlocked {count} businesses")
            messagebox.showinfo("Success", f"Unlocked {count} businesses successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unlock businesses: {str(e)}")
            self.status.config(text="Error unlocking businesses")

    def unlock_all_items_weeds(self):
        if not self.manager.current_save:
            messagebox.showwarning("Warning", "No save loaded!")
            self.status.config(text="No save loaded")
            return
        try:
            self.manager.unlock_all_items_weeds()
            self.status.config(text="Unlocked all items and weeds")
            messagebox.showinfo("Success", "Unlocked all items and weeds successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unlock items/weeds: {str(e)}")
            self.status.config(text="Error unlocking items/weeds")

    def recruit_all_dealers(self):
        if not self.manager.current_save:
            messagebox.showwarning("Warning", "No save loaded!")
            self.status.config(text="No save loaded")
            return
        try:
            count = self.manager.recruit_all_dealers()
            self.status.config(text=f"Recruited {count} dealers")
            messagebox.showinfo("Success", f"Recruited {count} dealers successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to recruit dealers: {str(e)}")
            self.status.config(text="Error recruiting dealers")

    def modify_variables(self):
        if not self.manager.current_save:
            messagebox.showwarning("Warning", "No save loaded!")
            self.status.config(text="No save loaded")
            return
        try:
            count = self.manager.modify_variables()
            self.status.config(text=f"Modified {count} variables")
            messagebox.showinfo("Success", f"Modified {count} variables successfully!")
            self.load_variables()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to modify variables: {str(e)}")
            self.status.config(text="Error modifying variables")

    def update_trash(self):
        if not self.manager.current_save:
            messagebox.showwarning("Warning", "No save loaded!")
            self.status.config(text="No save loaded")
            return
        try:
            count = self.manager.update_trash()
            self.status.config(text=f"Updated {count} trash items")
            messagebox.showinfo("Success", f"Updated {count} trash items successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update trash: {str(e)}")
            self.status.config(text="Error updating trash")

    def update_world_storage_entities(self):
        if not self.manager.current_save:
            messagebox.showwarning("Warning", "No save loaded!")
            self.status.config(text="No save loaded")
            return
        try:
            count = self.manager.update_world_storage_entities()
            self.status.config(text=f"Updated {count} world storage entities")
            messagebox.showinfo("Success", f"Updated {count} world storage entities successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update world storage: {str(e)}")
            self.status.config(text="Error updating world storage")

    def load_current_values(self):
        info = self.manager.get_save_info()
        money_mapping = {"Cash": "online_money", "Wealth": "networth", 
                        "Earnings": "lifetime_earnings", "Weekly Income": "weekly_deposit_sum"}
        for key, entry in self.money_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, str(info.get(money_mapping[key], 0)))

        rank_mapping = {"Level": "rank_number", "Sub-Level": "tier"}
        for key, entry in self.rank_entries.items():
            entry.delete(0, tk.END)
            if key in rank_mapping:
                entry.insert(0, str(info.get(rank_mapping[key], 0)))
            elif key == "Experience":
                entry.insert(0, "0")
            elif key == "Total Exp":
                entry.insert(0, "0")

        self.misc_entries["Gang Name"].delete(0, tk.END)
        self.misc_entries["Gang Name"].insert(0, info.get("organisation_name", ""))
        self.misc_entries["Time Played"].delete(0, tk.END)
        self.misc_entries["Time Played"].insert(0, str(info.get("play_time_seconds", 0)))
        self.misc_entries["Law Pressure"].delete(0, tk.END)
        self.misc_entries["Law Pressure"].insert(0, "1.0")

    def save_changes(self):
        try:
            self.manager.set_value("money", "OnlineBalance", float(self.money_entries["Cash"].get()))
            self.manager.set_value("money", "Networth", float(self.money_entries["Wealth"].get()))
            self.manager.set_value("money", "LifetimeEarnings", float(self.money_entries["Earnings"].get()))
            self.manager.set_value("money", "WeeklyDepositSum", float(self.money_entries["Weekly Income"].get()))
            self.manager.set_value("rank", "Rank", int(self.rank_entries["Level"].get()))
            self.manager.set_value("rank", "Tier", int(self.rank_entries["Sub-Level"].get()))
            self.manager.set_value("game", "OrganisationName", self.misc_entries["Gang Name"].get())
            self.manager.set_value("time", "Playtime", int(self.misc_entries["Time Played"].get()))
            
            self.status.config(text="Changes applied successfully")
            messagebox.showinfo("Success", "Changes applied successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes: {str(e)}")
            self.status.config(text="Error applying changes")

if __name__ == "__main__":
    root = tk.Tk()
    app = SaveEditor(root)
    root.mainloop()

