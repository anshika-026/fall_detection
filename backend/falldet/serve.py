"""python -m falldet.serve  (from the backend folder)"""
import multiprocessing

import uvicorn

from falldet import config

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run("falldet.main:app", host=config.HOST, port=config.PORT, log_level="info")
