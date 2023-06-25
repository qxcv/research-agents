"""

This script opens an html file and fills a list with dictionaries of information about each reference in the file. The dictionaries contain the following keys:
'inline' - the inline citation (e.g. 'Haarnoja et al., 2018')
'authors' - the authors of the paper (e.g. 'Haarnoja, T., Zhou, A., Abbeel, P., and Levine, S.')
'title' - the title of the paper (e.g. 'Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic Actor')
'id' - the id of the reference (e.g. 'bib.bib1')
'snippets' - a list of snippets of text that cite the reference

"""

from typing import Any, List, Dict, Tuple
from fuzzywuzzy import process
from research_agents import utils

from bs4 import BeautifulSoup
import re


def get_refs(html_string: str) -> List[Dict[str, str]]:
    # Create a BeautifulSoup object
    soup = BeautifulSoup(html_string, 'html.parser')
    
    refs = soup.find_all(id=re.compile('bib.bib[0-9]+$'))

    data = []
    for i, ref in enumerate(refs):
        ref = ref.text

        # Remove the unicode non-breaking space
        ref = ref.replace(u'\xa0', u' ')

        # Split the reference into lines
        ref_split = ref.splitlines()

        # Merge lines separated by empty lines
        ref = ''
        for line in ref_split:
            if line:
                ref += line + ' '
            else:
                ref += '\n'

        d_list = [s for s in ref.splitlines() if s]
        id = 'bib.bib' + str(i+1)
        
        links = soup.find_all(href='#'+id)
        snippets = []

        paras_to_extract = []
        para_set = set()
        for link in links:
            # para will be none if ref is in a footnote or caption (we don't
            # copy in this case)
            para = link.find_parent("p")
            if para is not None and para not in para_set:
                paras_to_extract.append(para)
                para_set.add(para)

        for para in paras_to_extract:
            snippet = ' '.join(para.text.splitlines())
            snippet = snippet.replace(u'\xa0', u' ')
            snippets.append(snippet)

        try:
            d = {
                'inline': d_list[0],
                'authors': d_list[1],
                'title': d_list[2],
                'id': 'bib.bib' + str(i+1),
                'snippets': snippets
            }
        except IndexError:
            print("Couldn't parse reference. d_list: ", d_list)
            continue

        data.append(d)

    return data


def find_ref_for(title: str, refs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Given a list of refs from get_ref, find the reference corresponding to
    the given paper title."""
    titles_lower = [d['title'].lower() for d in refs]
    result = process.extractOne(title.lower(), titles_lower, score_cutoff=50)
    if result is None:
        raise ValueError(f"Couldn't find a good match for {title=} in {titles_lower=}")
    best_title_lower = result[0]
    best_title_index = titles_lower.index(best_title_lower)
    return refs[best_title_index]


def simplify_whitespace(s: str) -> str:
    """Replace repeated whitespace with a single space and strip string.
    
    Good for processing individual <p> tags, etc."""
    return re.sub(r'\s+', ' ', s).strip()

def consolidate_whitespace(s: str) -> str:
    """Replace repeated copies of a type of whitespace (space, newline, tab,
    ...) with one copy of that same type."""
    s = re.sub(' +', ' ', s)  # Consolidate repeated spaces
    s = re.sub('\n+', '\n', s)  # Consolidate repeated newlines
    s = re.sub('\t+', '\t', s)  # Consolidate repeated tabs
    return s


def get_title_and_abstract(html_str: str) -> Tuple[str, str]:
    """Given an HTML string from ar5iv.org, return the title and abstract of the
    paper."""
    soup = BeautifulSoup(html_str, 'html.parser')
    title = soup.select('h1.ltx_title.ltx_title_document')
    if title is None:
        raise ValueError("Couldn't find title")
    title = simplify_whitespace(title[0].text)
    abstract = soup.select('div.ltx_abstract')
    if abstract is None:
        raise ValueError("Couldn't find abstract")
    abstract_raw = abstract[0].text
    if abstract_raw.startswith('Abstract'):
        abstract_raw = abstract_raw[len('Abstract'):].strip()
    abstract = simplify_whitespace(abstract_raw)
    return title, abstract


def get_kv_sections(html_str: str) -> Dict[str, str]:
    """Get a dictionary mapping section titles to section contents (as text)."""
    soup = BeautifulSoup(html_str, 'html.parser')
    sections = soup.select('section.ltx_section')
    if sections is None:
        sections = []
    result = {}
    for section in sections:
        title = section.select('h2.ltx_title.ltx_title_section')
        if title is None:
            continue
        title = simplify_whitespace(title[0].text)
        content = consolidate_whitespace(utils.render_bs4_element_to_markdown(section).strip())
        result[title] = content
    return result


def main() -> None:
    # Open the file
    with open('example-papers/curl.html', 'r') as f:
        # Read the file
        contents = f.read()

if __name__ == '__main__':
    main()

