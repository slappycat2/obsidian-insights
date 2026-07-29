from pathlib import Path
import json

from vault_check.v_chk_logger import logger

class JsonFile:
    """
    JsonFile class is used to load a JSON file and store its contents.
    Attributes:
        json_path (str): Path to the JSON file.
        json_data (dict): Parsed JSON data.
        err_msg (str): Error message if any exception occurs during loading.
    """
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.json_data = {}
        self.err_msg = ''

        try:
            with open(self.json_path, 'r', encoding='utf8') as f:
                self.json_data = json.load(f)

        except FileNotFoundError:
            self.err_msg = f"Exception: {json_path} not found. "

        except json.JSONDecodeError:
            self.err_msg = f"Exception: {json_path} is not a valid JSON file. "

        except Exception as e:
            raise Exception(f"JsonFile: load_json_file attempting to read: ({json_path}) - Error: {e}")

def main() -> None:
    pass

if __name__ == '__main__':
    main()



