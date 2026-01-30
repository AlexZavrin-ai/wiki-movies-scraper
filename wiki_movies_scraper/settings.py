# settings for the project.

BOT_NAME = "wiki_movies_scraper"

SPIDER_MODULES = ["wiki_movies_scraper.spiders"]
NEWSPIDER_MODULE = "wiki_movies_scraper.spiders"

ROBOTSTXT_OBEY = False

# Be polite
DOWNLOAD_DELAY = 0.7
CONCURRENT_REQUESTS = 4

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 5.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

