# Research Agent Package
# A modular system for autonomous research and report generation

import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler('research_agent.log')  # Log to file
    ]
)