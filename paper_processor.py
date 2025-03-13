"""
Module for processing PubMed paper data and identifying non-academic affiliations.
"""

from typing import Dict, List, Optional, Any, Tuple
import csv
import logging
import io
from datetime import datetime
from tqdm import tqdm

from pubmed_paper_fetcher.pubmed_api import PubMedAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PaperProcessor:
    """Class to process PubMed papers and identify those with non-academic affiliations."""
    
    def __init__(self, api: PubMedAPI, debug: bool = False):
        """
        Initialize the paper processor.
        
        Args:
            api: Initialized PubMedAPI instance
            debug: Whether to enable debug logging
        """
        self.api = api
        
        # Set logging level based on debug flag
        if debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
    
    def process_papers(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Process papers matching the query and identify those with non-academic affiliations.
        
        Args:
            query: PubMed search query
            max_results: Maximum number of results to process
            
        Returns:
            List of processed papers with non-academic affiliations
        """
        # Search for papers
        pmids = self.api.search_papers(query, max_results)
        
        # Process each paper
        processed_papers = []
        
        for pmid in tqdm(pmids, desc="Processing papers"):
            paper_data = self.api.fetch_paper_details(pmid)
            
            if not paper_data:
                logger.warning(f"Skipping PMID {pmid} due to missing data")
                continue
            
            processed_paper = self._process_single_paper(pmid, paper_data)
            if processed_paper and processed_paper.get("non_academic_authors"):
                processed_papers.append(processed_paper)
        
        logger.info(f"Found {len(processed_papers)} papers with non-academic affiliations")
        return processed_papers
    
    def _process_single_paper(self, pmid: str, paper_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single paper and extract relevant information.
        
        Args:
            pmid: PubMed ID of the paper
            paper_data: Paper data from PubMed API
            
        Returns:
            Processed paper data or None if processing fails
        """
        try:
            # Extract basic paper information
            article_data = paper_data.get("MedlineCitation", {}).get("Article", {})
            
            if not article_data:
                logger.debug(f"No article data found for PMID {pmid}")
                return None
            
            # Extract title
            title = article_data.get("ArticleTitle", "Unknown Title")
            
            # Extract publication date
            pub_date = self._extract_publication_date(article_data)
            
            # Extract corresponding author email
            corresponding_email = self.api.extract_corresponding_email(paper_data)
            
            # Process authors and their affiliations
            non_academic_authors = []
            company_affiliations = []
            
            if "AuthorList" in article_data:
                for author in article_data["AuthorList"]:
                    author_name = self._format_author_name(author)
                    
                    # Process affiliations
                    if "AffiliationInfo" in author:
                        for affiliation_info in author["AffiliationInfo"]:
                            affiliation = affiliation_info.get("Affiliation", "")
                            is_non_academic, company_name = self.api.is_non_academic_affiliation(affiliation)
                            
                            if is_non_academic and company_name:
                                non_academic_authors.append(author_name)
                                if company_name not in company_affiliations:
                                    company_affiliations.append(company_name)
            
            # Only return papers with non-academic affiliations
            if non_academic_authors:
                return {
                    "PubmedID": pmid,
                    "Title": title,
                    "Publication Date": pub_date,
                    "non_academic_authors": "; ".join(set(non_academic_authors)),
                    "company_affiliations": "; ".join(set(company_affiliations)),
                    "corresponding_email": corresponding_email or "Not available"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing paper {pmid}: {str(e)}")
            return None
    
    def _format_author_name(self, author: Dict[str, Any]) -> str:
        """
        Format author name from PubMed data.
        
        Args:
            author: Author data from PubMed
            
        Returns:
            Formatted author name
        """
        if "LastName" in author and "ForeName" in author:
            return f"{author['LastName']} {author['ForeName']}"
        elif "LastName" in author and "Initials" in author:
            return f"{author['LastName']} {author['Initials']}"
        elif "LastName" in author:
            return author["LastName"]
        elif "CollectiveName" in author:
            return author["CollectiveName"]
        else:
            return "Unknown Author"
    
    def _extract_publication_date(self, article_data: Dict[str, Any]) -> str:
        """
        Extract publication date from article data.
        
        Args:
            article_data: Article data from PubMed
            
        Returns:
            Formatted publication date
        """
        try:
            # Try to get date from PubDate
            if "Journal" in article_data and "JournalIssue" in article_data["Journal"]:
                journal_issue = article_data["Journal"]["JournalIssue"]
                
                if "PubDate" in journal_issue:
                    pub_date = journal_issue["PubDate"]
                    
                    # Handle different date formats
                    if "Year" in pub_date and "Month" in pub_date and "Day" in pub_date:
                        return f"{pub_date['Year']}-{pub_date['Month']}-{pub_date['Day']}"
                    elif "Year" in pub_date and "Month" in pub_date:
                        return f"{pub_date['Year']}-{pub_date['Month']}"
                    elif "Year" in pub_date:
                        return pub_date["Year"]
                    elif "MedlineDate" in pub_date:
                        # Extract year from MedlineDate
                        return pub_date["MedlineDate"].split()[0]
            
            # If we can't find a date, return unknown
            return "Unknown"
            
        except Exception as e:
            logger.debug(f"Error extracting publication date: {str(e)}")
            return "Unknown"
    
    def generate_csv(self, processed_papers: List[Dict[str, Any]]) -> str:
        """
        Generate CSV content from processed papers.
        
        Args:
            processed_papers: List of processed paper data
            
        Returns:
            CSV content as a string
        """
        if not processed_papers:
            return "No papers with non-academic affiliations found."
        
        # Define CSV columns
        fieldnames = [
            "PubmedID", 
            "Title", 
            "Publication Date", 
            "Non-academic Author(s)", 
            "Company Affiliation(s)", 
            "Corresponding Author Email"
        ]
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write data rows
        for paper in processed_papers:
            writer.writerow({
                "PubmedID": paper["PubmedID"],
                "Title": paper["Title"],
                "Publication Date": paper["Publication Date"],
                "Non-academic Author(s)": paper["non_academic_authors"],
                "Company Affiliation(s)": paper["company_affiliations"],
                "Corresponding Author Email": paper["corresponding_email"]
            })
        
        return output.getvalue()