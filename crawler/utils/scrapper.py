import os
import time
import json
import bs4
from abc import ABC, abstractmethod

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common import exceptions


class Article:
    def __init__(self, title, url, cat, desc, detail):
        self.title = title
        self.url = url
        self.cat = cat
        self.desc = desc
        self.detail = detail


class Scrapper(ABC):
    def __init__(self, limit=50, recursive=False):
        options = webdriver.ChromeOptions()
        options.add_argument("--log-level=3")
        options.add_argument("start-maximized")
        options.add_argument("enable-automation")
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-browser-side-navigation")
        options.add_argument("--disable-gpu")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_experimental_option(
            "prefs", {"profile.managed_default_content_settings.images": 2}
        )

        self.driver = webdriver.Chrome(options=options)

        self.limit = limit
        self.recursive = recursive

    @abstractmethod
    def get_article_urls(self) -> list[str]:
        pass

    @abstractmethod
    def get_articles(self) -> list[Article]:
        pass


class VnExpressScrapper(Scrapper):
    """
    Scrapper for VnExpress.
    """

    def _get_article_urls(self, url: str) -> set[str]:
        """
        Get all article urls from a given url.

        #### Parameters:
            - url: The url to get the article urls from.

        #### Returns:
            - article_urls: A set of article urls.
        """
        # Get webpage content
        self.driver.get(url)

        # self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        # time.sleep(1)
        # self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")

        # Parse html and select the relevent tag
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        articles = soup.select("h3.title-news a")

        # Extract all article urls
        article_urls = set()
        for article in articles:
            # Get the article url
            article_url = article.get("href")
            # Check if the url is valid
            if isinstance(article_url, str) and "vnexpress.net/" in article_url:
                article_url = article_url.replace("#box_comment_vne", "")
                # Add url to list
                article_urls.add(article_url)
            else:
                print("Error: article_url is not valid", article_url)
        return article_urls

    def get_article_urls(self) -> list[str]:
        """
        Get all article urls.
        """
        # article_urls = set()
        url = "https://vnexpress.net/"
        if os.path.exists("vne_url.json"):
            with open("vne_url.json", "r") as f:
                urls = set(json.load(f))
        else:
            urls = set()
        if self.recursive:
            article_urls = self._get_article_urls(url)
            # List of articles to check for sub-articles
            checking_article_urls = article_urls.copy()
            # Get all sub-articles
            while len(article_urls) < self.limit and len(checking_article_urls) > 0:
                new_article_urls = set()
                for article_url in checking_article_urls:
                    new_article_urls.update(self._get_article_urls(article_url))
                # Get all new urls that are not in the list of articles for next check
                checking_article_urls = new_article_urls.difference(article_urls)
                # Add all new urls to the list of articles
                article_urls.update(new_article_urls)
            urls.update(article_urls)
        else:
            urls = self._get_article_urls(url)

        with open("vne_url.json", "w", encoding="utf8") as f:
            json.dump(list(urls), f, ensure_ascii=False)
        return list(urls)

    def get_articles(self) -> list[Article]:
        """
        Get all articles.
        """
        # Check if "vne.json" exists, if exists load and return it
        # If not continue
        if os.path.exists("vne.json"):
            with open("vne.json", "r", encoding="utf8") as f:
                articles = []
                json_articles = json.load(f)
                for json_article in json_articles:
                    articles.append(
                        Article(
                            json_article["title"],
                            json_article["url"],
                            json_article["cat"],
                            json_article["desc"],
                            json_article["detail"],
                        )
                    )
            return articles

        # Check if "vne_url.json" file contains list of article_urls exists, if exists load from it
        # if it doesn't exist, call get_article_urls()
        if os.path.exists("vne_url.json"):
            with open("vne_url.json", "r", encoding="utf8") as f:
                article_urls = json.load(f)
        else:
            article_urls = self.get_article_urls()
            with open("vne_url.json", "w", encoding="utf8") as f:
                json.dump(article_urls, f, ensure_ascii=False)

        # Get all articles
        articles: list[Article] = []
        try:
            for article_url in article_urls:
                # Get webpage content
                self.driver.get(article_url)
                # self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                # time.sleep(0.5)
                # Parse html and select the relevent tag
                soup = BeautifulSoup(self.driver.page_source, "html.parser")

                # Check if podcast and print out for debugging
                tag = soup.select_one("div.title-folder a")
                if tag is not None and tag.text.strip() == "Podcasts":
                    print("Podcast found:", article_url)
                    continue

                # Get title
                tag = (
                    soup.select_one("h1.title-detail")  # Normal news title
                    # or soup.select_one("h1.title-news")  # Podcasts?
                    # or soup.select_one("h1.title")  # IDK
                )
                if tag is None:
                    # raise ValueError("Error: title is not found")
                    print("Error: title is not found", article_url)
                    continue
                title = tag.text.strip()

                # Get category
                tag = soup.select_one("ul.breadcrumb li:nth-of-type(1) a")
                if tag is None:
                    # raise ValueError("Error: category is not found")
                    cat = ""
                else:
                    cat = tag.text.strip()

                # Get article content
                tag = soup.select_one(
                    "p.description"
                ) or soup.select_one(  # Normal news description / Podcasts
                    "p.lead_detail"
                )  # IDK
                if tag is None:
                    # raise ValueError("Error: description is not found")
                    desc = ""
                else:
                    # Set desc as the first children that has type bs4.element.NavigableString
                    desc = next(
                        (
                            x
                            for x in tag.children
                            if type(x) == "bs4.element.NavigableString"
                        ),
                        "",
                    )

                # Get article detail
                tag = soup.select("article.fck_detail p.Normal")
                if len(tag) == 0:
                    # raise ValueError("Error: detail is not found")
                    detail = ""
                else:
                    detail = " ".join(map(lambda x: x.text.strip(), tag))

                # Create article object
                articles.append(Article(title, article_url, cat, desc, detail))
        except exceptions.TimeoutException:
            pass

        # Save articles to file
        json_articles = []
        for article in articles:
            json_articles.append(article.__dict__)
        with open("vne.json", "w", encoding="utf8") as f:
            json.dump(json_articles, f, ensure_ascii=False)
        return articles


class BaoMoiScrapper(Scrapper):
    def get_article_urls(self) -> list[str]:
        page = 1
        article_urls = set()
        while len(article_urls) < self.limit:
            # Get webpage content
            self.driver.get(f"https://baomoi.com/trang{page}.epi")
            # Parse html and select the relevent tag
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            if len(soup.select("div.bm_q div.bm_w h3.bm_F a")) == 0:
                break
            articles = soup.select("div.bm_w h3.bm_F a")
            article_urls.update(articles)
            page += 1

        # Extract all article urls
        urls = set()
        for article in article_urls:
            # Get the article url
            article_url = article.get("href")
            urls.add(article_url)

        with open("bm_url.json", "w", encoding="utf8") as f:
            json.dump(list(urls), f, ensure_ascii=False)
        return list(urls)

    def get_articles(self) -> list[Article]:
        if os.path.exists("bm_url.json"):
            with open("bm_url.json", "r", encoding="utf8") as f:
                article_urls = json.load(f)
        else:
            article_urls = self.get_article_urls()
            with open("bm_url.json", "w", encoding="utf8") as f:
                json.dump(article_urls, f, ensure_ascii=False)

        articles: list[Article] = []
        for url in article_urls:
            print(f"Getting article: {url}")
            self.driver.get(f"https://baomoi.com{url}")
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            tag = soup.select_one("div.bm_AX h1.bm_F")
            if tag is None:
                print("Error: title is not found", url)
                continue
            title = tag.text.strip()

            tag = soup.select_one("div.bm_T a.bm_U:nth-of-type(1)")
            if tag is None:
                print("Error: category is not found", url)
                cat = ""
            else:
                cat = tag.text.strip()
            
            tag = soup.select_one("div.bm_AX h3.bm_F.bm_x")
            if tag is None:
                print("Error: description is not found", url)
                desc = ""
            else:
                desc = tag.text.strip()

            detail = " ".join(map(lambda x: x.text.strip(), soup.select("p.bm_AS:not(.bm_RM)")))

            articles.append(
                Article(title, f"https://baomoi.com{url}", cat, desc, detail)
            )
        
        # Save articles to file
        json_articles = []
        for article in articles:
            json_articles.append(article.__dict__)
        with open("bm.json", "w", encoding="utf8") as f:
            json.dump(json_articles, f, ensure_ascii=False)
        return articles
