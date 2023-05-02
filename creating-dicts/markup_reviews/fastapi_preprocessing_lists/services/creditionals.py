import os

from dotenv import load_dotenv

load_dotenv()

DB = {os.getenv("USERNAME"): {"password": os.getenv("PASSWORD")}}
print(DB)
