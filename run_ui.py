import os
from app.web.server import run


if __name__ == "__main__":
    run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8765")))


