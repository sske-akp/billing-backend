from fastapi import FastAPI
from app.main import app


# Vercel expects a handler named 'handler'
def handler(event, context):
    from vercel_fastapi import VercelFastAPI

    return VercelFastAPI(app).handler(event, context)
