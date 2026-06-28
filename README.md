# pravenc-md

*Православная энциклопедия* (*Orthodox Encyclopedia*) articles in Markdown format.

This repository contains the articles published in the electronic version converted to Markdown format. It is intended for purposes of search, querying, and machine learning.

The repository also contains scripts:
- extract_urls.py: extracts article URLs from the complete listing of encyclopedia articles found at (this page)[https://pravenc.ru/list.html] (note that the upper bound is hardcoded in the script and needs to be updated manually when they add more articles, now it has been set to 376); writes its output to article_urls.txt.

- batch_scrape.py: downloads the URLs listed in urls.txt and converts the resulting files to Markdown, recording them in articles/. If a Markdown file already exits, skips, so we are downloading only new URLs.
