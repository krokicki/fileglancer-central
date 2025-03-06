#!/usr/bin/env python
"""
Download file share paths from the Janelia wiki and save to the Fileglancer database.
Based on documentation at https://atlassian-python-api.readthedocs.io/confluence.html#get-page-info

To use this script you must create a Personal Access Token and save it into your environment:
https://wikis.janelia.org/plugins/personalaccesstokens/usertokens.action
"""

from io import StringIO
import pandas as pd
from datetime import datetime
from atlassian import Confluence
from .settings import get_settings
from loguru import logger
settings = get_settings()

confluence_space = "SCS"
confluence_page = "Lab and Project File Share Paths"

def parse_iso_timestamp(timestamp):
    """Parse ISO format timestamp string to datetime object"""
    return datetime.fromisoformat(timestamp)


def get_wiki_table(confluence_url, confluence_token):
    """Fetch and parse the file share paths table from the wiki"""
    confluence = Confluence(url=str(confluence_url), token=confluence_token)
    
    page = confluence.get_page_by_title(confluence_space, confluence_page)
    page_id = page['id']
    page = confluence.get_page_by_id(page_id, status=None, version=None,
                expand="body.view,metadata.labels,ancestors,history,history.lastUpdated")

    # Get the last updated timestamp for the table
    table_last_updated = None
    if 'lastUpdated' in page['history']:
        table_last_updated = parse_iso_timestamp(page['history']['lastUpdated']['when'])

    body = page['body']['view']['value']
    tables = pd.read_html(StringIO(body))
    table = tables[0]

    # Fill missing values in the table from above values
    for column in table.columns:
        last_valid_value = None
        for index, value in table[column].items():
            if pd.isna(value):
                table.at[index, column] = last_valid_value
            else:
                last_valid_value = value
    
    column_names = ('lab', 'storage', 'mac_path', 'windows_path', 'linux_path', 'group')
    table.columns = column_names

    logger.debug(f"Found {len(table)} file share paths in the wiki")  
    return table, table_last_updated
