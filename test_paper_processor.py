"""
Tests for the Paper Processor module.
"""

import unittest
from unittest.mock import patch, MagicMock

from pubmed_paper_fetcher.paper_processor import PaperProcessor
from pubmed_paper_fetcher.pubmed_api import PubMedAPI

class TestPaperProcessor(unittest.TestCase):
    """Test cases for the PaperProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api = MagicMock(spec=PubMedAPI)
        self.processor = PaperProcessor(self.api)
    
    def test_format_author_name(self):
        """Test formatting of author names."""
        # Test with ForeName and LastName
        author = {"LastName": "Smith", "ForeName": "John"}
        self.assertEqual(self.processor._format_author_name(author), "Smith John")
        
        # Test with Initials and LastName
        author = {"LastName": "Johnson", "Initials": "AB"}
        self.assertEqual(self.processor._format_author_name(author), "Johnson AB")
        
        # Test with LastName only
        author = {"LastName": "Williams"}
        self.assertEqual(self.processor._format_author_name(author), "Williams")
        
        # Test with CollectiveName
        author = {"CollectiveName": "COVID-19 Research Group"}
        self.assertEqual(self.processor._format_author_name(author), "COVID-19 Research Group")
        
        # Test with empty author
        author = {}
        self.assertEqual(self.processor._format_author_name(author), "Unknown Author")
    
    def test_extract_publication_date(self):
        """Test extraction of publication dates."""
        # Test with Year, Month, and Day
        article_data = {
            "Journal": {
                "JournalIssue": {
                    "PubDate": {
                        "Year": "2023",
                        "Month": "Jan",
                        "Day": "15"
                    }
                }
            }
        }
        self.assertEqual(self.processor._extract_publication_date(article_data), "2023-Jan-15")
        
        # Test with Year and Month
        article_data = {
            "Journal": {
                "JournalIssue": {
                    "PubDate": {
                        "Year": "2022",
                        "Month": "Dec"
                    }
                }
            }
        }
        self.assertEqual(self.processor._extract_publication_date(article_data), "2022-Dec")
        
        # Test with Year only
        article_data = {
            "Journal": {
                "JournalIssue": {
                    "PubDate": {
                        "Year": "2021"
                    }
                }
            }
        }
        self.assertEqual(self.processor._extract_publication_date(article_data), "2021")
        
        # Test with MedlineDate
        article_data = {
            "Journal": {
                "JournalIssue": {
                    "PubDate": {
                        "MedlineDate": "2020 Winter"
                    }
                }
            }
        }
        self.assertEqual(self.processor._extract_publication_date(article_data), "2020")
        
        # Test with missing data
        article_data = {}
        self.assertEqual(self.processor._extract_publication_date(article_data), "Unknown")
    
    @patch('pubmed_paper_fetcher.paper_processor.tqdm')
    def test_process_papers(self, mock_tqdm):
        """Test processing of papers."""
        # Mock API responses
        self.api.search_papers.return_value = ["12345", "67890"]
        
        # Mock paper details
        paper_data_1 = {
            "MedlineCitation": {
                "Article": {
                    "ArticleTitle": "Test Paper 1",
                    "Journal": {
                        "JournalIssue": {
                            "PubDate": {"Year": "2023"}
                        }
                    },
                    "AuthorList": [
                        {
                            "LastName": "Smith",
                            "ForeName": "John",
                            "AffiliationInfo": [
                                {"Affiliation": "Pfizer Inc., New York, NY, USA"}
                            ]
                        }
                    ]
                }
            }
        }
        
        paper_data_2 = {
            "MedlineCitation": {
                "Article": {
                    "ArticleTitle": "Test Paper 2",
                    "Journal": {
                        "JournalIssue": {
                            "PubDate": {"Year": "2022"}
                        }
                    },
                    "AuthorList": [
                        {
                            "LastName": "Johnson",
                            "ForeName": "Alice",
                            "AffiliationInfo": [
                                {"Affiliation": "Harvard University, Boston, MA, USA"}
                            ]
                        }
                    ]
                }
            }
        }
        
        # Set up API mock returns
        self.api.fetch_paper_details.side_effect = [paper_data_1, paper_data_2]
        self.api.is_non_academic_affiliation.side_effect = [(True, "Pfizer Inc."), (False, None)]
        self.api.extract_corresponding_email.return_value = "john.smith@pfizer.com"
        
        # Mock tqdm to return the original iterable
        mock_tqdm.return_value = ["12345", "67890"]
        
        # Call the method
        result = self.processor.process_papers("test query", max_results=2)
        
        # Verify the result
        self.assertEqual(len(result), 1)  # Only one paper has non-academic affiliation
        self.assertEqual(result[0]["PubmedID"], "12345")
        self.assertEqual(result[0]["Title"], "Test Paper 1")
        self.assertEqual(result[0]["Publication Date"], "2023")
        self.assertEqual(result[0]["non_academic_authors"], "Smith John")
        self.assertEqual(result[0]["company_affiliations"], "Pfizer Inc.")
        self.assertEqual(result[0]["corresponding_email"], "john.smith@pfizer.com")
        
        # Verify API calls
        self.api.search_papers.assert_called_once_with("test query", 2)
        self.assertEqual(self.api.fetch_paper_details.call_count, 2)

if __name__ == "__main__":
    unittest.main()