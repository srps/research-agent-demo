from openai import OpenAI
import requests
import json
import logging
from typing import List, Dict, Any, Optional

class WebSearchAgent:
    """Handles web searches and summarization of search results."""
    
    def __init__(self):
        """Initialize the web search module."""
        self.logger = logging.getLogger(__name__)
    
    def search(self, query, api_key, context=None):
        """Execute a web search for the given query.
        
        Args:
            query (str): The search query
            api_key (str): OpenAI API key
            context (dict, optional): Research context for more focused searching
        """
        client = OpenAI(api_key=api_key)
        
        # Enhance query with context if available
        if context and context.get('latest_decision'):
            decision = context['latest_decision']
            query = f"{query} (considering: {decision.get('reasoning', '')})"
        
        # Log the search request
        self.logger.debug(f"Executing web search for query: {query}")
        
        import time
        start_time = time.time()
        
        # Execute the search using OpenAI's Responses API with web search tool
        response = client.responses.create(
            model="gpt-4o-mini",
            tools=[{"type": "web_search_preview"}],
            input=f"Search for information about: {query}",
        )
        
        # Calculate and log response time
        response_time = time.time() - start_time
        self.logger.info(f"Received search response in {response_time:.2f} seconds")
        
        # Log detailed response information
        self.logger.debug("OpenAI API Search Response Details:")
        self.logger.debug(f"Raw response: {response}")
        self.logger.debug(f"Response ID: {response.id if hasattr(response, 'id') else 'N/A'}")
        self.logger.debug(f"Model used: {response.model if hasattr(response, 'model') else 'N/A'}")
        self.logger.debug(f"Response created: {response.created if hasattr(response, 'created') else 'N/A'}")
        
        # Extract the search results
        search_results = []
        
        # Process the response to extract search results
        for output_item in response.output:
            if output_item.type == "message" and hasattr(output_item, "content"):
                for content_item in output_item.content:
                    if content_item.type == "output_text" and hasattr(content_item, "annotations"):
                        # Extract citations as search results
                        for annotation in content_item.annotations:
                            if annotation.type == "url_citation":
                                # Extract the text that references this citation
                                citation_text = content_item.text[annotation.start_index:annotation.end_index]
                                
                                # Include timestamp for citation tracking
                                from datetime import datetime
                                search_results.append({
                                    "title": annotation.title or "Web Search Result",
                                    "link": annotation.url,
                                    "snippet": citation_text,
                                    "accessed_date": datetime.now(),
                                    "annotation": {
                                        "start_index": annotation.start_index,
                                        "end_index": annotation.end_index,
                                        "type": annotation.type
                                    }
                                })
        
        # If no search results were found in annotations, create a generic one with the full response
        if not search_results and response.output:
            for output_item in response.output:
                if output_item.type == "message" and hasattr(output_item, "content"):
                    for content_item in output_item.content:
                        if content_item.type == "output_text":
                            # Include timestamp for citation tracking even for generic results
                            from datetime import datetime
                            search_results.append({
                                "title": "OpenAI Web Search Result",
                                "link": "",  # No specific link available
                                "snippet": content_item.text,
                                "accessed_date": datetime.now()
                            })
        
        return search_results
    
    def summarize(self, search_results, query, api_key, context=None):
        """Summarize search results.
        
        Args:
            search_results (list): List of search results
            query (str): The original query
            api_key (str): OpenAI API key
            context (dict, optional): Research context for better summarization
            
        Returns:
            dict: A dictionary containing the summary text and any annotations for citations
        """
        # Initialize the OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Format the search results for the prompt
        formatted_results = ""
        for i, result in enumerate(search_results):
            formatted_results += f"Result {i+1}:\n"
            formatted_results += f"Title: {result['title']}\n"
            formatted_results += f"URL: {result['link']}\n"
            formatted_results += f"Snippet: {result['snippet']}\n\n"
        
        # Add context to summarization prompt if available
        context_prompt = ""
        if context and context.get('latest_decision'):
            context_prompt = f"\nConsider this context from previous research: {context['latest_decision'].get('reasoning', '')}"
        
        # Create input text for the response API
        input_text = f"""I'm researching the following topic: '{query}'
        
        Here are some search results I found:{context_prompt}
        
        {formatted_results}
        
        Please provide a comprehensive summary of the key information from these search results that's relevant to my research topic. 
        Include important facts, definitions, and insights. 
        Organize the information logically and make it easy to understand.
        If there are conflicting viewpoints, please note them.
        Focus particularly on addressing any gaps or questions raised in the previous research context."""

        # Call the OpenAI API using the responses endpoint
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "You are a research assistant that summarizes web search results into clear, concise, and informative summaries."
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": input_text
                        }
                    ]
                }
            ],
            text={
                "format": {
                    "type": "text",
                    "max_tokens": 2000
                }
            },
            reasoning={
                "effort": "low"
            },
            tools=[],
            store=True
        )
        
        # Log response details
        self.logger.debug("OpenAI API Response Details:")
        self.logger.debug(f"Raw response: {response}")
        self.logger.debug(f"Response ID: {response.id if hasattr(response, 'id') else 'N/A'}")
        self.logger.debug(f"Model used: {response.model if hasattr(response, 'model') else 'N/A'}")
        
        # Extract the summary from the response and process any annotations
        summary = ""
        annotations = []
        full_text = ""
        citation_map = {}
        
        # First pass: collect all content and build the full text
        for output_item in response.output:
            if output_item.type == "message" and hasattr(output_item, "content"):
                for content_item in output_item.content:
                    if content_item.type == "output_text":
                        # Store the full text for later processing
                        full_text += content_item.text
                        
                        # Process annotations and build a citation map
                        if hasattr(content_item, "annotations") and content_item.annotations:
                            for annotation in content_item.annotations:
                                if annotation.type == "url_citation":
                                    # Create a unique identifier for this citation
                                    from datetime import datetime
                                    citation_id = f"citation_{len(citation_map) + 1}"
                                    
                                    # Store citation details with their positions in the text
                                    citation_map[citation_id] = {
                                        "title": annotation.title or "Web Search Result",
                                        "url": annotation.url,
                                        "snippet": content_item.text[annotation.start_index:annotation.end_index],
                                        "accessed_date": datetime.now(),
                                        "annotation": {
                                            "start_index": annotation.start_index,
                                            "end_index": annotation.end_index,
                                            "type": annotation.type
                                        }
                                    }
        
        # Set the summary to the full text with annotations preserved
        summary = full_text
        
        # Convert the citation map to a list for compatibility with existing code
        for citation_id, citation_data in citation_map.items():
            annotations.append({
                "id": citation_id,
                "title": citation_data["title"],
                "url": citation_data["url"],
                "snippet": citation_data["snippet"],
                "accessed_date": citation_data["accessed_date"],
                "annotation": citation_data["annotation"]
            })
        
        # Return both the summary and any annotations found
        return {
            "summary": summary.strip(),
            "annotations": annotations
        }
    
