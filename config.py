import os

import dotenv

dotenv.load_dotenv()

API_KEY = os.getenv("ZAI_API_KEY")
BASE_URL = "https://api.z.ai/api/coding/paas/v4"
MODEL = "glm-4.7"
