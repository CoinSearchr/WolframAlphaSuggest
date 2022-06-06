

from . import app, cache
from . import db
from . import common

import random
import time
import subprocess
from apscheduler.schedulers.background import BackgroundScheduler

logger = app.logger #logging.getLogger(__name__)

def task_refresh_dns_cache():
    """ Ensures that the API is loaded into the local DNS cache to minimize latency. """

    #logger.info(f"Doing periodic WA API call to keep DNS cache fresh. 'random int' -> '{common.wa_simple_lookup('random int')}'.")

    stime = time.time()

    try:
        subprocess.check_call(["dig", "api.wolframalpha.com"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e: # subprocess.CalledProcessError
        logger.warning(f"Dig DNS query failed: {e}")

    #logger.info(f"Done DNS cache call in {time.time()-stime:.4f}s.")

def init_bg_tasks():
    scheduler = BackgroundScheduler()
    job = scheduler.add_job(task_refresh_dns_cache, 'interval', seconds=5)
    scheduler.start()

    logger.info(f"init_bg_tasks() complete.")
