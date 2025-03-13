from setuptools import setup, find_packages

setup(
    name="pubmed_paper_fetcher",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "get-papers-list=pubmed_paper_fetcher.cli:main",
        ],
    },
)