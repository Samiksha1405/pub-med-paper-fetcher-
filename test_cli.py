"""
Tests for the command-line interface.
"""

import unittest
from unittest.mock import patch, MagicMock
import io
import sys

from pubmed_paper_fetcher.cli import main, parse_args

class TestCLI(unittest.TestCase):
    """Test cases for the command-line interface."""
    
    def test_parse_args_basic(self):
        """Test basic argument parsing."""
        args = parse_args(["cancer therapy"])
        self.assertEqual(args.query, "cancer therapy")
        self.assertFalse(args.debug)
        self.assertIsNone(args.file)
        self.assertEqual(args.max_results, 100)
        self.assertEqual(args.email, "user@example.com")
        self.assertIsNone(args.api_key)
    
    def test_parse_args_full(self):
        """Test parsing all arguments."""
        args = parse_args([
            "cancer therapy",
            "--debug",
            "--file", "output.csv",
            "--max-results", "50",
            "--email", "test@example.com",
            "--api-key", "abc123"
        ])
        self.assertEqual(args.query, "cancer therapy")
        self.assertTrue(args.debug)
        self.assertEqual(args.file, "output.csv")
        self.assertEqual(args.max_results, 50)
        self.assertEqual(args.email, "test@example.com")
        self.assertEqual(args.api_key, "abc123")
    
    @patch('pubmed_paper_fetcher.cli.PubMedAPI')
    @patch('pubmed_paper_fetcher.cli.PaperProcessor')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_main_success(self, mock_stdout, mock_processor_class, mock_api_class):
        """Test successful execution of main function."""
        # Set up mocks
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor
        
        # Mock processor methods
        mock_processor.process_papers.return_value = [
            {
                "PubmedID": "12345",
                "Title": "Test Paper",
                "Publication Date": "2023",
                "non_academic_authors": "Smith John",
                "company_affiliations": "Pfizer Inc.",
                "corresponding_email": "john.smith@pfizer.com"
            }
        ]
        
        mock_processor.generate_csv.return_value = "CSV content"
        
        # Call main function
        result = main(["cancer therapy"])
        
        # Verify result
        self.assertEqual(result, 0)
        
        # Verify API and processor were initialized correctly
        mock_api_class.assert_called_once_with(
            email="user@example.com",
            api_key=None,
            tool="get-papers-list"
        )
        
        mock_processor_class.assert_called_once_with(mock_api, debug=False)
        
        # Verify processor methods were called correctly
        mock_processor.process_papers.assert_called_once_with(
            query="cancer therapy",
            max_results=100
        )
        
        mock_processor.generate_csv.assert_called_once()
        
        # Verify output
        self.assertEqual(mock_stdout.getvalue().strip(), "CSV content")
    
    @patch('pubmed_paper_fetcher.cli.PubMedAPI')
    @patch('pubmed_paper_fetcher.cli.PaperProcessor')
    def test_main_with_file_output(self, mock_processor_class, mock_api_class):
        """Test main function with file output."""
        # Set up mocks
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor
        
        # Mock processor methods
        mock_processor.process_papers.return_value = [
            {
                "PubmedID": "12345",
                "Title": "Test Paper",
                "Publication Date": "2023",
                "non_academic_authors": "Smith John",
                "company_affiliations": "Pfizer Inc.",
                "corresponding_email": "john.smith@pfizer.com"
            }
        ]
        
        mock_processor.generate_csv.return_value = "CSV content"
        
        # Mock open function
        mock_open = MagicMock()
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch('builtins.open', mock_open):
            # Call main function with file output
            result = main(["cancer therapy", "--file", "output.csv"])
            
            # Verify result
            self.assertEqual(result, 0)
            
            # Verify file was opened and written to
            mock_open.assert_called_once_with("output.csv", 'w', encoding='utf-8')
            mock_file.write.assert_called_once_with("CSV content")
    
    @patch('pubmed_paper_fetcher.cli.PubMedAPI')
    def test_main_error(self, mock_api_class):
        """Test main function with error."""
        # Set up mock to raise exception
        mock_api_class.side_effect = Exception("Test error")
        
        # Call main function
        result = main(["cancer therapy"])
        
        # Verify non-zero exit code
        self.assertNotEqual(result, 0)

if __name__ == "__main__":
    unittest.main()