"""
Tests for the PubMed API module.
"""

import unittest
from unittest.mock import patch, MagicMock

from pubmed_paper_fetcher.pubmed_api import PubMedAPI

class TestPubMedAPI(unittest.TestCase):
    """Test cases for the PubMedAPI class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api = PubMedAPI(email="test@example.com")
    
    def test_is_non_academic_affiliation_company(self):
        """Test identification of company affiliations."""
        # Test obvious company affiliations
        affiliation = "Pfizer Inc., New York, NY, USA"
        is_company, company_name = self.api.is_non_academic_affiliation(affiliation)
        self.assertTrue(is_company)
        self.assertEqual(company_name, "Pfizer Inc.")
        
        affiliation = "Genentech, Inc., South San Francisco, CA 94080, USA"
        is_company, company_name = self.api.is_non_academic_affiliation(affiliation)
        self.assertTrue(is_company)
        self.assertEqual(company_name, "Genentech, Inc.")
    
    def test_is_non_academic_affiliation_academic(self):
        """Test identification of academic affiliations."""
        # Test obvious academic affiliations
        affiliation = "Department of Biology, Stanford University, Stanford, CA, USA"
        is_company, company_name = self.api.is_non_academic_affiliation(affiliation)
        self.assertFalse(is_company)
        self.assertIsNone(company_name)
        
        affiliation = "Harvard Medical School, Boston, MA, USA"
        is_company, company_name = self.api.is_non_academic_affiliation(affiliation)
        self.assertFalse(is_company)
        self.assertIsNone(company_name)
    
    @patch('pubmed_paper_fetcher.pubmed_api.Entrez')
    def test_search_papers(self, mock_entrez):
        """Test searching for papers."""
        # Mock Entrez.esearch and Entrez.read
        mock_handle = MagicMock()
        mock_entrez.esearch.return_value = mock_handle
        mock_entrez.read.return_value = {"IdList": ["12345", "67890"]}
        
        # Call the method
        result = self.api.search_papers("cancer therapy", max_results=10)
        
        # Verify the result
        self.assertEqual(result, ["12345", "67890"])
        
        # Verify Entrez.esearch was called with the correct parameters
        mock_entrez.esearch.assert_called_once_with(
            db="pubmed", term="cancer therapy", retmax=10
        )

if __name__ == "__main__":
    unittest.main()