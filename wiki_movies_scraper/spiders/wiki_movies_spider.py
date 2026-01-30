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

    # Доп.задание: попытаться собрать рейтинг IMDb (0/1)
    with_imdb = 0

    def start_requests(self):
        url = getattr(self, "start_url", self.start_url)
        self.max_movies = int(getattr(self, "max_movies", self.max_movies))
        self.with_imdb = int(getattr(self, "with_imdb", self.with_imdb))

        # счётчик фильмов
        self.movie_count = 0

        yield scrapy.Request(url, callback=self.parse_category)

    def parse_category(self, response):
        """Парсим страницу категории Википедии.

        В Википедии категории часто состоят из:
        - подкатегорий (например, "Фильмы по годам" -> "Фильмы 2020 года")
        - страниц (непосредственно страницы фильмов)

        Поэтому мы:
        1) обходим подкатегории (callback=parse_category)
        2) обходим страницы фильмов (callback=parse_movie)
        """

        if self.movie_count >= self.max_movies:
            return

        # 1) Подкатегории
        subcat_hrefs = response.css("#mw-subcategories a::attr(href)").getall()
        for href in subcat_hrefs:
            if self.movie_count >= self.max_movies:
                return
            if not href:
                continue
            # В Википедии подкатегории имеют вид /wiki/Категория:...
            if href.startswith("/wiki/%D0%9A%D0%B0%D1%82%D0%B5%D0%B3%D0%BE%D1%80%D0%B8%D1%8F:") or href.startswith("/wiki/Категория:"):
                yield scrapy.Request(response.urljoin(href), callback=self.parse_category)

        # 2) Страницы фильмов внутри "Страницы в категории"
        page_hrefs = response.css("#mw-pages div.mw-category a::attr(href)").getall()
        if not page_hrefs:
            # Фолбэк для некоторых страниц
            page_hrefs = response.css("div.mw-category a::attr(href)").getall()

        for href in page_hrefs:
            if self.movie_count >= self.max_movies:
                return
            if not href or not href.startswith("/wiki/"):
                continue

            url = response.urljoin(href)
            yield scrapy.Request(url, callback=self.parse_movie)

        # 3) Пагинация "Следующая страница" (обычно внутри блока #mw-pages)
        next_href = response.xpath("//div[@id='mw-pages']//a[contains(., 'Следующая страница')]/@href").get()
        if next_href and self.movie_count < self.max_movies:
            yield scrapy.Request(response.urljoin(next_href), callback=self.parse_category)

    def parse_movie(self, response):
        if self.movie_count >= self.max_movies:
            return
        self.movie_count += 1

        # Заголовок статьи (в Википедии текст обычно лежит внутри <span class="mw-page-title-main">)
        title_parts = response.css("h1#firstHeading ::text").getall()
        title = " ".join([t.strip() for t in title_parts if t.strip()])
        title = re.sub(r"\s+", " ", title).strip()

        # Поля из инфобокса (карточка справа)
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

        # Доп. задание: IMDb rating
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

        # Рейтинг часто лежит в JSON-LD:
        # <script type="application/ld+json"> ... "aggregateRating": {"ratingValue": "..."} ...
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

    # ---------------- helpers ----------------

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
        # 1) Ищем внешние ссылки на imdb.com/title/tt....
        hrefs = response.css("a.external::attr(href)").getall()
        for h in hrefs:
            if not h:
                continue
            m = re.search(r"imdb\.com/title/(tt\d+)", h)
            if m:
                return m.group(1)

        # 2) Иногда IMDb ID встречается прямо в html страницы
        html = response.text
        m = re.search(r"(tt\d{6,10})", html)
        if m:
            return m.group(1)

        return None
