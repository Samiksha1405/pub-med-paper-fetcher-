"""
Command-line interface for the PubMed Paper Fetcher.
"""

import argparse
import sys
import logging
from typing import List, Optional

from pubmed_paper_fetcher.pubmed_api import PubMedAPI
from pubmed_paper_fetcher.paper_processor import PaperProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: Command-line arguments (defaults to sys.argv[1:])
        
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Fetch research papers from PubMed with pharmaceutical/biotech company affiliations"
    )
    
    parser.add_argument(
        "query",
        help="PubMed search query (supports full PubMed query syntax)"
    )
    
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Print debug information during execution"
    )
    
    parser.add_argument(
        "-f", "--file",
        help="Specify the filename to save the results (if not provided, print to console)"
    )
    
    parser.add_argument(
        "-m", "--max-results",
        type=int,
        default=100,
        help="Maximum number of results to fetch (default: 100)"
    )
    
    parser.add_argument(
        "-e", "--email",
        default="user@example.com",
        help="Email address to identify yourself to NCBI (required)"
    )
    
    parser.add_argument(
        "-k", "--api-key",
        help="NCBI API key for higher request limits"
    )
    
    return parser.parse_args(args)

def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the command-line interface.
    
    Args:
        args: Command-line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parsed_args = parse_args(args)
    
    # Set logging level based on debug flag
    if parsed_args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("pubmed_paper_fetcher").setLevel(logging.DEBUG)
    
    try:
        # Initialize API client
        api = PubMedAPI(
            email=parsed_args.email,
            api_key=parsed_args.api_key,
            tool="get-papers-list"
        )
        
        # Initialize paper processor
        processor = PaperProcessor(api, debug=parsed_args.debug)
        
        # Process papers
        logger.info(f"Fetching papers for query: {parsed_args.query}")
        processed_papers = processor.process_papers(
            query=parsed_args.query,
            max_results=parsed_args.max_results
        )
        
        # Generate CSV
        csv_content = processor.generate_csv(processed_papers)
        
        # Output results
        if parsed_args.file:
            with open(parsed_args.file, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            logger.info(f"Results saved to {parsed_args.file}")
        else:
            print(csv_content)
        
        logger.info(f"Found {len(processed_papers)} papers with non-academic affiliations")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        if parsed_args.debug:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())