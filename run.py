import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"==================================================")
    print(f" Starting SupportGenie AI (PS04) on http://{settings.HOST}:{settings.PORT}")
    print(f"==================================================")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
