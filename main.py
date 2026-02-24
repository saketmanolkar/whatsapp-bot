import logging

from fastapi import FastAPI

from routes.webhook import router as webhook_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI()
app.include_router(webhook_router)
