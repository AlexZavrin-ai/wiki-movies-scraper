# Minimal settings for the project.
# You can change USER_AGENT / DOWNLOAD_DELAY if the site blocks you.

BOT_NAME = "wiki_movies_scraper"

SPIDER_MODULES = ["wiki_movies_scraper.spiders"]
NEWSPIDER_MODULE = "wiki_movies_scraper.spiders"

# For учебных задач часто выключают robots.txt, чтобы доп.источники (IMDb) работали.
# Если преподаватель требует соблюдать robots.txt — поставь True,
# но тогда IMDb рейтинг может не собираться.
ROBOTSTXT_OBEY = False

# Be polite
DOWNLOAD_DELAY = 0.7
CONCURRENT_REQUESTS = 4

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 5.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# We don't need pipelines — we export to CSV with:
# scrapy crawl wiki_movies -O movies.csv

# Чтобы Excel/Windows корректно открывали CSV с кириллицей
FEED_EXPORT_ENCODING = "utf-8-sig"
