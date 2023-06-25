import requests
import time
import re
import dbm
from research_agents.utils import RateLimiter
import typing
from bs4 import BeautifulSoup
import requests
import json

_global_rate_limiter = RateLimiter(2)  # limit to 2 req/s
_prophy_cache_path = 'prophy_cache.dbm'


def check_cache(check_str: str) -> typing.Optional[str]:
    with dbm.open(_prophy_cache_path, 'c') as cache:
        if check_str in cache:
            return cache[check_str].decode("utf-8")
        
def save_cache(key: str, value: str) -> None:
    with dbm.open(_prophy_cache_path, 'c') as cache:
        cache[key] = value.encode("utf-8")

def get_url(url: str, timeout:float=10.0) -> requests.Response:
    _global_rate_limiter.wait()
    response = requests.get(url, timeout=timeout, allow_redirects=True)
    if response.status_code != 200:
        raise ValueError(f"Server gave status code {response.status_code} for {url}")
    save_cache(url, response.text)
    return response


def get_arxiv_id(arxiv_identifier: str) -> str:
    """
    Extract the arXiv ID from an identifier (either a URL or a numeric ID).
    """
    identifier_re = re.compile(r".*\b(?P<numeric_id>[0-9]{4}\.[0-9]{5})(v[0-9]+)?\b.*")
    match = identifier_re.match(arxiv_identifier)
    if match is None:
        raise ValueError("Invalid arXiv identifier: {}".format(arxiv_identifier))

    # get the numeric ID (without the optional version)
    numeric_id = match.group("numeric_id")
    return numeric_id

def prophy_extract_article_data(numeric_id: str, timeout:float=10.0) -> typing.List[str]:
    # check the local cache
    page_html = check_cache(numeric_id)
    if page_html is None:
        _global_rate_limiter.wait()
        # URL to send the request to
        url = 'https://www.prophy.science/api/graphql/'

        # Payload to send in the request
        payload = {
            "operationName": "found",
            "query": "query found($query: String!, $selectors: [GSelector]!, $ranges: [GSelectedRange]!, $sort: String, $conceptIds: [String], $page: Int) {\n  found: search(query: $query, selectors: $selectors, ranges: $ranges, sort: $sort, size: 30, page: $page) {\n    searchLimit\n    searchLimitReason\n    currentSearchCount\n    total\n    nextPage\n    hits {\n      score\n      explain\n      contexts\n      highlightedTitle\n      highlightedAbstract\n      article {\n        id\n        title\n        abstract\n        year\n        citationsCount\n        origins {\n          originId\n          code\n          url\n          __typename\n        }\n        concepts(highlightedConcepts: $conceptIds) {\n          conceptId\n          name\n          tf\n          basic\n          highlight\n          __typename\n        }\n        authors {\n          name\n          authorId\n          __typename\n        }\n        journal {\n          journalId\n          shortTitle\n          volume\n          issue\n          pages\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    facets {\n      authors {\n        title\n        code\n        count\n        __typename\n      }\n      journals {\n        title\n        code\n        count\n        __typename\n      }\n      hasFulltext {\n        title\n        code\n        count\n        __typename\n      }\n      publicationsYears {\n        key\n        count\n        __typename\n      }\n      __typename\n    }\n    topConcepts {\n      conceptId\n      name\n      df\n      __typename\n    }\n    __typename\n  }\n}\n",
            "variables": {
                "query": f'{{"condition":"OR","children":[{{"name":"arxiv:{numeric_id}"}}]}}',
                "selectors": [],
                "ranges": [],
                # Add the rest of your variables here
            }
        }

        # Set headers
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Send the request
        response = requests.post(url, data=json.dumps(payload), headers=headers)

        # TODO: handle errors
        page_html = response.json()
    else:
        page_html = json.loads(page_html)
    
    article = page_html['data']['found']['hits'][0]['article']
    id = article['id']
    title = article['title']
    # Split title by spaces and remove non-alphanumeric characters
    title_list = re.sub(r'\W+', ' ', title).split()
    # Remove empty strings
    title_list = [x for x in title_list if x != '']
    # Create the URL
    article_url = f'https://www.prophy.science/article/{"-".join([str(id)] + title_list)}/'
    
    article_text = check_cache(article_url)
    if article_text is None:
        response = get_url(article_url, timeout=10)  # TODO: handle errors
        article_text = response.text
    
    soup = BeautifulSoup(article_text, 'html.parser')

    title = soup.find('title').text
    # If the title contains " - Prophy", remove it
    title = title.replace(' - Prophy', '')
    abstract = soup.find(class_=["col-md-9", "col-sm-8", "col-xs-12"]).find('p').text

    return title, abstract, id

def prophy_extract_citing_links(article_id: str,
                                timeout:float=10.0,
                                offset: int=0) -> typing.List[str]:
    full_article_url = f"https://www.prophy.science/references-to/article/{article_id}/?offset={offset}&sort=citations"
    article_text = check_cache(full_article_url)
    if article_text is None:
        response = requests.get(full_article_url)  # TODO: handle errors
        article_text = response.text
    # print(f'Full article URL: {full_article_url}')
    soup = BeautifulSoup(article_text, 'html.parser')
    # Find all the links with hrefs which start with /article
    link_divs = soup.find_all('li')
    link_urls = []
    for link_div in link_divs:
        str_with_year = link_div.find('div').get_text()
        year = ''
        for char in str_with_year:
            if char.isdigit():
                year += char
            else:
                break
        if not len(year) == 4 and year[:2] == '20':
            print(f'WEIRDNESS!!!', year, link_div)
            continue
        if year == '2023':
            print('skipping 2023')
            continue
        link = link_div.find('a').get('href')
        if not link.startswith('/article'):
            print(f'WEIRDNESS!!!', link)
            continue
        link_urls.append(link) 
    return link_urls

def prophy_find_citing_data(article_url: str, timeout:float=10.0) -> typing.Dict[str, str]:
    article_url = f'https://www.prophy.science{article_url}'
    # print(f'Citing article URL: {article_url}')
    article_text = check_cache(article_url)
    if article_text is None:
        response = get_url(article_url, timeout=timeout)  # TODO: handle errors
        article_text = response.text
    soup = BeautifulSoup(article_text, 'html.parser')
    abstract = soup.find(class_=["col-md-9", "col-sm-8", "col-xs-12"])
    abstract = abstract.find('p').text
    arxiv = soup.find(class_="origins").find('a').text.strip()
    title = soup.find('title').text
    # If the title contains " - Prophy", remove it
    title = title.replace(' - Prophy', '')
    
    return {
        'arxiv': arxiv,
        'title': title,
        'abstract': abstract,
    }
    
    

def download_prophy(arxiv_identifier: str, *,
                    timeout: float=10.0,
                    num_most_cited: int=10,
                    ) -> typing.List[typing.Dict[str, str]]:
    """Download the HTML of an arXiv paper via ar5iv.
    
    Args:
        arxiv_identifier: A numeric identify (XXXX.YYYYY) or arXiv URL
            identifying the paper.
        timeout: The maximum time to wait for a response from the server.
        
    Returns:
        Two lists of subsets of papers which cite the given paper:
              the num_most_cited most papers and the num_most_recent. If there are not enough
              papers, the lists will be shorter than the requested length.
              The papers are tuples of (arxiv_id, title, authors, abstract, citation_count, year).
        # TODO: this is a lie
        .""" 
    arxiv_id = get_arxiv_id(arxiv_identifier)
    title, abstract, article_id = prophy_extract_article_data(arxiv_id, timeout=timeout)
    citing_links = []
    for offset in range(0, num_most_cited, 10):  
        citing_links += prophy_extract_citing_links(article_id,
                                                    timeout=timeout,
                                                    offset=offset)
    citing_data = []
    for link in citing_links:
        citing_data.append(prophy_find_citing_data(link, timeout=timeout))
        
    return title, abstract, citing_data


if __name__ == '__main__':
    # fetch some papers as a test
    start = time.time()