import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MODE = os.getenv("DYNAMO_MODE", "local")
    PRODUCTS_TABLE = os.getenv("PRODUCTS_TABLE", "ShopSphere_Products")
    REVIEWS_TABLE = os.getenv("REVIEWS_TABLE", "ShopSphere_Reviews")
    REGION = os.getenv("AWS_REGION", "us-east-1")

    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "fakeAccessKeyId")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "fakeSecretAccessKey")
    AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", "")
