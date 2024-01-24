from utils.scrapper import *
from pprint import pprint
import json
import logging

logger = logging.getLogger('selenium')
logger.setLevel(logging.DEBUG)


scrapper = BaoMoiScrapper(1000, True)
articles = scrapper.get_articles()
# scrapper.get_article_urls()
pass