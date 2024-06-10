from masa.types.web import WebScraperObject

def web_scraper_parser(web_scraper_responses):
    return [
        [WebScraperObject(**item) for item in response]
        for response in web_scraper_responses  # Each response is a list of dictionaries
    ]

