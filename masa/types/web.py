from typing import List, Optional
from typing_extensions import TypedDict

class Section(TypedDict, total=False):
    title: str
    paragraphs: Optional[List[str]]
    images: Optional[List[str]]

class WebScraperObject(TypedDict):
    sections: Optional[List[Section]]
    pages: List[str]