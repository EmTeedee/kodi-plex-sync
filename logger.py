"""Standard logger for this project"""
import sys
import logging
import yaml

with open("config.yml", "r", encoding="utf-8") as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)

# get log level from config
log_level = getattr(logging, cfg["log"]["level"].upper(), None)
if not isinstance(log_level, int):
    raise ValueError(f"Invalid log level: {cfg['log']['level']}")

logger = logging.getLogger('kodiplex')
logger.setLevel(log_level)

# create file handler which logs up to debug messages
fh = logging.FileHandler('kodiplex.log')
fh.setLevel(logging.DEBUG)

# create console handler which logs notset/debug/info to stdout and
# warning/error/critical to stderr
ch_out = logging.StreamHandler(sys.stdout)
ch_out.setLevel(logging.DEBUG)
ch_out.addFilter(lambda record: record.levelno <= logging.INFO)
ch_err = logging.StreamHandler(sys.stderr)
ch_err.setLevel(logging.WARNING)

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch_out.setFormatter(formatter)
ch_err.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch_out)
logger.addHandler(ch_err)
