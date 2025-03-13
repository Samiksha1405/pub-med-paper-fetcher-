"""
Module for interacting with the PubMed API to fetch research papers.
"""

from typing import Dict, List, Optional, Any, Tuple
import time
import re
import logging
from urllib.parse import quote

import requests
from Bio import Entrez

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PubMedAPI:
    """Class to interact with the PubMed API using Biopython's Entrez module."""
    
    def __init__(self, email: str, api_key: Optional[str] = None, tool: str = "PubMedPaperFetcher"):
        """
        Initialize the PubMed API client.
        
        Args:
            email: Email address to identify yourself to NCBI
            api_key: Optional NCBI API key for higher request limits
            tool: Name of the tool making the request
        """
        self.email = email
        self.api_key = api_key
        self.tool = tool
        
        # Set up Entrez
        Entrez.email = email
        Entrez.tool = tool
        if api_key:
            Entrez.api_key = api_key
            
        # Rate limiting parameters
        self.request_delay = 0.34  # seconds between requests (3 requests per second with API key)
        if not api_key:
            self.request_delay = 1.0  # 1 request per second without API key
            
        self.last_request_time = 0.0
    
    def _rate_limit(self) -> None:
        """Implement rate limiting for API requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.request_delay:
            sleep_time = self.request_delay - time_since_last_request
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def search_papers(self, query: str, max_results: int = 100) -> List[str]:
        """
        Search for papers in PubMed based on the provided query.
        
        Args:
            query: PubMed search query
            max_results: Maximum number of results to return
            
        Returns:
            List of PubMed IDs matching the query
        """
        logger.info(f"Searching PubMed with query: {query}")
        self._rate_limit()
        
        try:
            # Search for papers
            handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
            record = Entrez.read(handle)
            handle.close()
            
            pmids = record["IdList"]
            logger.info(f"Found {len(pmids)} papers matching the query")
            return pmids
        
        except Exception as e:
            logger.error(f"Error searching PubMed: {str(e)}")
            raise
    
    def fetch_paper_details(self, pmid: str) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific paper by PubMed ID.
        
        Args:
            pmid: PubMed ID of the paper
            
        Returns:
            Dictionary containing paper details
        """
        logger.debug(f"Fetching details for paper with PMID: {pmid}")
        self._rate_limit()
        
        try:
            # Fetch paper details
            handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
            records = Entrez.read(handle)
            handle.close()
            
            if not records["PubmedArticle"]:
                logger.warning(f"No details found for PMID: {pmid}")
                return {}
            
            article = records["PubmedArticle"][0]
            return article
        
        except Exception as e:
            logger.error(f"Error fetching paper details for PMID {pmid}: {str(e)}")
            return {}
    
    def is_non_academic_affiliation(self, affiliation: str) -> Tuple[bool, Optional[str]]:
        """
        Determine if an affiliation is from a pharmaceutical/biotech company.
        
        Args:
            affiliation: Author affiliation string
            
        Returns:
            Tuple of (is_non_academic, company_name)
        """
        # Keywords that indicate academic institutions
        academic_keywords = [
            "university", "college", "institute", "school", "academy", 
            "hospital", "clinic", "medical center", "health center",
            "laboratory", "national", "federal", "ministry", "department of",
            "center for", "research center", "foundation", "association"
        ]
        
        # Keywords that indicate pharmaceutical/biotech companies
        company_keywords = [
            "pharma", "biotech", "therapeutics", "biosciences", "inc", "llc", 
            "ltd", "limited", "corp", "corporation", "co.", "company", "gmbh",
            "laboratories", "labs", "biopharma", "pharmaceuticals"
        ]
        
        # Check if affiliation contains company indicators but not academic indicators
        affiliation_lower = affiliation.lower()
        
        # First check for obvious company indicators
        for keyword in company_keywords:
            if keyword in affiliation_lower:
                # Make sure it's not an academic institution with a similar name
                is_academic = any(academic_kw in affiliation_lower for academic_kw in academic_keywords)
                if not is_academic:
                    # Try to extract company name
                    company_name = self._extract_company_name(affiliation)
                    return True, company_name
        
        # Check for absence of academic keywords as another indicator
        if not any(keyword in affiliation_lower for keyword in academic_keywords):
            # If no academic keywords and has "," which often separates company from location
            if "," in affiliation:
                company_name = self._extract_company_name(affiliation)
                return True, company_name
        
        return False, None
    
    def _extract_company_name(self, affiliation: str) -> str:
        """
        Extract company name from affiliation string.
        
        Args:
            affiliation: Author affiliation string
            
        Returns:
            Extracted company name or original affiliation if extraction fails
        """
        # Try to extract company name before the first comma
        if "," in affiliation:
            potential_company = affiliation.split(",")[0].strip()
            if len(potential_company) > 3 and len(potential_company) < 50:
                return potential_company
        
        # If no comma or extraction failed, return the first 50 chars
        return affiliation[:50].strip()
    
    def extract_corresponding_email(self, article: Dict[str, Any]) -> Optional[str]:
        """
        Extract the corresponding author's email from the article data.
        
        Args:
            article: Article data from PubMed
            
        Returns:
            Email address of the corresponding author, if available
        """
        try:
            # Try to find email in the author list
            if "MedlineCitation" in article and "Article" in article["MedlineCitation"]:
                article_data = article["MedlineCitation"]["Article"]
                
                # Check if author list exists
                if "AuthorList" in article_data:
                    for author in article_data["AuthorList"]:
                        if "AffiliationInfo" in author:
                            for affiliation in author["AffiliationInfo"]:
                                if "Affiliation" in affiliation:
                                    # Look for email pattern in affiliation
                                    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', affiliation["Affiliation"])
                                    if email_match:
                                        return email_match.group(0)
            
            # Try to find in the article data
            article_str = str(article)
            email_matches = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', article_str)
            if email_matches:
                return email_matches[0]
                
        except Exception as e:
            logger.debug(f"Error extracting email: {str(e)}")
            
        return None