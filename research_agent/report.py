import openai
from openai import OpenAI
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

class ReportGeneratorError(Exception):
    """Custom exception for ReportGenerator errors"""
    pass

class ReportGenerator:
    """Generates a final research report in Markdown format based on collected summaries."""
    
    def __init__(self):
        """Initialize the report generator."""
        self.logger = logging.getLogger(__name__)
    
    def generate_report(self, topic: str, research_plan: Any, research_summaries: List[Dict], api_key: str) -> str:
        """Generate a comprehensive research report based on the collected summaries.
        
        Args:
            topic (str): The original research topic
            research_plan (Any): The research plan steps
            research_summaries (List[Dict]): List of research summaries collected
            api_key (str): OpenAI API key
            
        Returns:
            str: A markdown-formatted research report
            
        Raises:
            ReportGeneratorError: If there's an error during report generation
        """
        try:
            if not api_key:
                raise ReportGeneratorError("OpenAI API key is required")
            
            if not topic:
                raise ReportGeneratorError("Research topic is required")
                
            if not research_summaries:
                raise ReportGeneratorError("No research summaries provided")

            self.logger.debug("Input validation passed")
            client = OpenAI(api_key=api_key)
            self.logger.debug("OpenAI client initialized")
            
            self.logger.debug(f"Generating research report for topic: {topic}")
            
            try:
                self.logger.debug("Formatting research plan...")
                # Format the research plan and summaries for the prompt
                formatted_plan = "\n".join([f"- {step}" for step in research_plan])
                self.logger.debug("Research plan formatted successfully")
                
                self.logger.debug("Formatting summaries and citations...")
                formatted_summaries = ""
                formatted_citations = ""
                citation_index = 1
                citation_map = {}
                
                for i, summary in enumerate(research_summaries):
                    self.logger.debug(f"Processing summary {i+1}/{len(research_summaries)}")
                    if not isinstance(summary, dict):
                        raise ReportGeneratorError(f"Invalid summary format at index {i}")
                    
                    formatted_summaries += f"## Research on: {summary.get('task', 'Unknown Task')}\n\n"
                    formatted_summaries += f"{summary.get('summary', 'No summary available')}\n\n"
                    
                    # Handle annotations/citations if they exist in the summary
                    if 'annotations' in summary and summary['annotations']:
                        citation_refs = []
                        
                        for annotation in summary['annotations']:
                            citation_key = f"[{citation_index}]"
                            citation_refs.append(citation_key)
                            
                            # Store citation information in the citation map
                            citation_map[citation_key] = {
                                "title": annotation.get("title", "Untitled"),
                                "url": annotation.get("url", "No URL available"),
                                "accessed_date": annotation.get("accessed_date", datetime.now().isoformat())[:10],  # YYYY-MM-DD
                                "snippet": annotation.get("snippet", ""),
                                "annotation": annotation.get("annotation", None),
                                "id": annotation.get("id", f"citation_{citation_index}")
                            }
                            citation_index += 1
                        
                        # Instead of just listing sources at the end, we'll preserve the original text with citations
                        # This maintains the inline citation format from the API response
                        summary_text = summary.get('summary', 'No summary available')
                        
                        # Add the summary with properly formatted citations
                        formatted_summaries += f"{summary_text}\n\n"
                        
                        # Add a list of sources at the end of each summary section for reference
                        formatted_summaries += "Sources: " + ", ".join(citation_refs) + "\n\n"
                
                self.logger.debug("Summaries and citations formatted successfully")
                
                if citation_map:
                    formatted_citations = "\n## Bibliography\n\n"
                    for key, citation in citation_map.items():
                        formatted_citations += f"{key} {citation['title']}. Available at: {citation['url']} (Accessed: {citation['accessed_date']})\n\n"
                
                self.logger.debug("Creating prompt...")
                # Create prompt for the LLM
                prompt = f"""I've been researching the topic: '{topic}'
                
                My research plan was:
                {formatted_plan}
                
                Here are the summaries of my research:
                
                {formatted_summaries}
                
                {formatted_citations}
                
                Please create a comprehensive, well-structured research report in Markdown format based on this information.
                
                The report should:
                1. Have a clear title and introduction explaining the topic
                2. Be organized into logical sections with appropriate headings
                3. Present the information in a coherent narrative that flows well
                4. Include relevant facts, insights, and analysis from the research summaries
                5. Maintain all citation references from the research summaries in your report
                6. Include the bibliography section at the end of the report
                7. Have a conclusion that summarizes the key findings
                
                Format the report using proper Markdown syntax with headings, bullet points, emphasis, etc.
                """
                
                self.logger.debug(f"Prompt created, length: {len(prompt)} characters")
                
                import time
                start_time = time.time()
                
                try:
                    # Call the OpenAI API
                    response = client.responses.create(
                        model="gpt-4o-mini",
                        input=[
                            {
                                "role": "system",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": "You are a research report writer that creates comprehensive, well-structured reports in Markdown format."
                                    }
                                ]
                            },
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": prompt
                                    }
                                ]
                            }
                        ],
                        temperature=0.7,
                        tools=[],
                        store=True
                    )
                    self.logger.debug("API call completed")
                    
                    response_time = time.time() - start_time
                    self.logger.info(f"Received report generation response in {response_time:.2f} seconds")
                    
                    if response.error:
                        error_msg = f"API Error ({response.error.code}): {response.error.message}"
                        self.logger.error(error_msg)
                        raise ReportGeneratorError(error_msg)
                    
                    report = response.output_text
                    
                    if not report:
                        raise ReportGeneratorError("Generated report is empty")
                    
                    self.logger.debug(f"Generated report length: {len(report)} characters")
                    return report
                    
                except openai.APIError as e:
                    self.logger.error(f"OpenAI API error: {str(e)}")
                    raise ReportGeneratorError(f"OpenAI API error: {str(e)}")
                except openai.APIConnectionError as e:
                    self.logger.error(f"Connection error: {str(e)}")
                    raise ReportGeneratorError(f"Error connecting to OpenAI API: {str(e)}")
                except openai.RateLimitError as e:
                    self.logger.error(f"Rate limit error: {str(e)}")
                    raise ReportGeneratorError(f"OpenAI API rate limit exceeded: {str(e)}")
                except openai.APITimeoutError as e:
                    self.logger.error(f"Timeout error: {str(e)}")
                    raise ReportGeneratorError(f"OpenAI API request timed out: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Unexpected API error: {str(e)}")
                    raise ReportGeneratorError(f"Error calling OpenAI API: {str(e)}")
                
            except Exception as e:
                self.logger.error(f"Error in formatting data: {str(e)}")
                raise ReportGeneratorError(f"Error formatting research data: {str(e)}")
            
        except ReportGeneratorError as e:
            self.logger.error(f"Report generation error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise ReportGeneratorError(f"Unexpected error in report generation: {str(e)}")
