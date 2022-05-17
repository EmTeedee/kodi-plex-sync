import logging
import yaml

with open("config.yml", "r") as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)

# get log level from config
log_level = getattr(logging, cfg["log"]["level"].upper(), None)
if not isinstance(log_level, int):
    raise ValueError('Invalid log level: %s' % cfg["log"]["level"])

logger = logging.getLogger('kodiplex')
logger.setLevel(log_level)

# create file handler which logs up to debug messages
fh = logging.FileHandler('kodiplex.log')
fh.setLevel(logging.DEBUG)

# create console handler which logs up to info
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)