import datetime
import os
import csv

from config import BASE_LOG_PATH, START_DATE
base_path_logger = BASE_LOG_PATH



def setup_logger(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd = open(path, 'a')  # Open in append mode
    return fd


#quantx/logs/20250205/5
def get_current_log_path(start_date, update_minutes):
    current_log_path = f"{base_path_logger}/{start_date}/{update_minutes}"
    return current_log_path

