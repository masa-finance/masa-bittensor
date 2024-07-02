from masa.types.web import WebScraperObject


def web_scraper_parser(web_scraper_responses):
    return [WebScraperObject(**response) for response in web_scraper_responses]
