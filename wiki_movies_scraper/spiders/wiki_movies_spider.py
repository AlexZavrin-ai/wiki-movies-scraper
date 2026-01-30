import re
import json
import scrapy


class WikiMoviesSpider(scrapy.Spider):
    name = "wiki_movies"
    allowed_domains = ["ru.wikipedia.org", "www.imdb.com"]

    # Можно передать стартовую страницу в командной строке:
    # scrapy crawl wiki_movies -a start_url="https://ru.wikipedia.org/wiki/Категория:Фильмы_по_алфавиту" -O movies.csv
    start_url = "https://ru.wikipedia.org/wiki/Категория:Фильмы_по_алфавиту"

    # Ограничение, чтобы случайно не скачать десятки тысяч фильмов
    max_movies = 200

    #собрать рейтинг IMDb (0/1)
    with_imdb = 0

    def start_requests(self):
        url = getattr(self, "start_url", self.start_url)
        self.max_movies = int(getattr(self, "max_movies", self.max_movies))
        self.with_imdb = int(getattr(self, "with_imdb", self.with_imdb))

        # счётчик фильмов
        self.movie_count = 0

        yield scrapy.Request(url, callback=self.parse_category)

    def parse_category(self, response):
        # Ссылки на страницы фильмов (в категории)
        links = response.css("div.mw-category a::attr(href)").getall()
        for href in links:
            if self.movie_count >= self.max_movies:
                return
            if not href or not href.startswith("/wiki/"):
                continue

            url = response.urljoin(href)
            yield scrapy.Request(url, callback=self.parse_movie)

        # Следующая страница категории (если есть)
        next_href = response.css("a:contains('Следующая страница')::attr(href)").get()
        if next_href and self.movie_count < self.max_movies:
            yield scrapy.Request(response.urljoin(next_href), callback=self.parse_category)

    def parse_movie(self, response):
        if self.movie_count >= self.max_movies:
            return
        self.movie_count += 1

        title = response.css("h1#firstHeading::text").get()
        if title:
            title = title.strip()

        # доп поля
        genre = self._get_infobox_value(response, ["Жанр", "Жанры"])
        director = self._get_infobox_value(response, ["Режиссёр", "Режиссер", "Режиссёры"])
        country = self._get_infobox_value(response, ["Страна", "Страны"])
        year = self._guess_year(response)

        item = {
            "title": title,
            "genre": genre,
            "director": director,
            "country": country,
            "year": year,
            "imdb_rating": "",
        }

        # IMDb
        if self.with_imdb:
            imdb_id = self._extract_imdb_id(response)
            if imdb_id:
                imdb_url = f"https://www.imdb.com/title/{imdb_id}/"
                yield scrapy.Request(
                    imdb_url,
                    callback=self.parse_imdb,
                    meta={"item": item},
                    headers={"Accept-Language": "en-US,en;q=0.9"},
                )
                return

        yield item

    def parse_imdb(self, response):
        item = response.meta.get("item", {})

    
        text = response.css("script[type='application/ld+json']::text").get()
        rating = ""
        if text:
            try:
                data = json.loads(text.strip())
                agg = data.get("aggregateRating") or {}
                rating = agg.get("ratingValue") or ""
            except Exception:
                rating = ""

        item["imdb_rating"] = str(rating).strip()
        yield item

 

    def _get_infobox_value(self, response, keys):
        # Ищем строку инфобокса по заголовку (th) и берём значение из (td)
        for k in keys:
            row = response.xpath(
                "//table[contains(@class,'infobox')]//tr[th[contains(normalize-space(.), $k)]]",
                k=k,
            )
            if row:
                val = row.xpath(".//td//text()").getall()
                val = " ".join([v.strip() for v in val if v.strip()])
                val = re.sub(r"\s+", " ", val).strip()
                if val:
                    return val
        return ""

    def _guess_year(self, response):
        # 1) Пробуем инфобокс: Год / Премьера и т.п.
        txt = self._get_infobox_value(response, ["Год", "Год выхода", "Премьера"])
        m = re.search(r"(19\d{2}|20\d{2})", txt or "")
        if m:
            return m.group(1)

        # 2) Фолбэк: первые абзацы
        text = " ".join(response.css("div.mw-parser-output > p::text").getall())
        m = re.search(r"(19\d{2}|20\d{2})", text)
        if m:
            return m.group(1)

        return ""

    def _extract_imdb_id(self, response):
        # 1) Поиск внешних ссылок на imdb.com
        hrefs = response.css("a.external::attr(href)").getall()
        for h in hrefs:
            if not h:
                continue
            m = re.search(r"imdb\.com/title/(tt\d+)", h)
            if m:
                return m.group(1)

        # 2) на случай если  IMDb ID встречается прямо в html страницы
        html = response.text
        m = re.search(r"(tt\d{6,10})", html)
        if m:
            return m.group(1)

        return None
