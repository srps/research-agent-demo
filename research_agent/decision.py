from openai import OpenAI
import logging
import json
from .models import ResearchDecision

class DecisionModuleError(Exception):
    """Custom exception for DecisionModule errors"""
    pass

class DecisionModule:
    """Determines when enough research has been done to generate a final report."""
    
    def __init__(self):
        """Initialize the decision module."""
        self.logger = logging.getLogger(__name__)
    
    def is_research_complete(self, research_summaries, topic, api_key):
        """Check if enough research has been done to answer the research topic.
        
        Args:
            research_summaries (list): List of research summaries collected so far
            topic (str): The original research topic
            api_key (str): OpenAI API key
            
        Returns:
            ResearchDecision: A decision object with completion status and reasoning
            
        Raises:
            DecisionModuleError: If there's an error with the API call or response processing
        """
        # If we have no summaries, research is not complete
        if not research_summaries:
            return ResearchDecision(
                is_complete=False,
                reasoning="No research has been conducted yet.",
                gaps=["All aspects of the topic need to be researched."],
            )
        
        try:
            # Initialize the OpenAI client with the API key
            client = OpenAI(api_key=api_key)
            
            self.logger.debug(f"Evaluating research completion for topic: {topic}")
            
            # Format the research summaries for the prompt
            formatted_summaries = ""
            for i, summary in enumerate(research_summaries):
                formatted_summaries += f"Research Step {i+1}: {summary['task']}\n"
                formatted_summaries += f"Summary: {summary['summary']}\n\n"
            
            # Create a prompt for the LLM
            prompt = f"""I'm researching the topic: '{topic}'
            
            So far, I've collected the following research summaries:
            
            {formatted_summaries}
            
            Based on these summaries, do I have enough information to create a comprehensive research report on the topic? 
            Consider whether the key aspects of the topic have been covered and if there are any significant gaps in the research.
            
            Please provide your assessment in the following JSON format:
            {{
                "is_complete": true/false,
                "reasoning": "Your detailed explanation of why the research is or is not complete",
                "gaps": ["List specific areas or questions that still need to be researched"]
            }}
            """
            
            # Log the request
            self.logger.debug(f"Sending request to OpenAI API with prompt length: {len(prompt)} characters")
            
            import time
            start_time = time.time()
            
            try:
                # Call the OpenAI API using the responses endpoint with JSON schema
                response = client.responses.create(
                    model="gpt-4o-mini",
                    input=[
                        {
                            "role": "system",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    text={
                        "format": {
                          "type": "json_schema",
                          "name": "research_decision",
                          "strict": True,
                          "schema": {
                            "type": "object",
                            "properties": {
                              "is_complete": {
                                "type": "boolean",
                                "description": "Whether the research is considered complete"
                              },
                              "reasoning": {
                                "type": "string",
                                "description": "Explanation of why the research is or is not complete"
                              },
                              "gaps": {
                                "type": "array",
                                "description": "Specific gaps in the research that need to be addressed",
                                "items": {
                                  "type": "string"
                                }
                              }
                            },
                            "required": [
                              "is_complete",
                              "reasoning",
                              "gaps"
                            ],
                            "additionalProperties": False
                          }
                        }
                      },
                    tools=[],
                    store=True
                )
            except Exception as e:
                error_msg = f"API call failed: {str(e)}"
                self.logger.error(error_msg)
                raise DecisionModuleError(error_msg)
            
            # Calculate and log response time
            response_time = time.time() - start_time
            self.logger.info(f"Received decision response in {response_time:.2f} seconds")
            
            # Log detailed response information
            self.logger.debug("OpenAI API Response Details:")
            self.logger.debug(f"Raw response: {response}")
            self.logger.debug(f"Response ID: {response.id if hasattr(response, 'id') else 'N/A'}")
            self.logger.debug(f"Model used: {response.model if hasattr(response, 'model') else 'N/A'}")
            self.logger.debug(f"Response created: {response.created if hasattr(response, 'created') else 'N/A'}")
            
            # Check for API errors in the response
            if response.error:
                error_msg = f"API Error ({response.error.code}): {response.error.message}"
                self.logger.error(error_msg)
                raise DecisionModuleError(error_msg)
            
            try:
                # Extract the decision from the response
                json_response = json.loads(response.output_text)
                self.logger.debug(f"Response JSON: {json_response}")
                
                # Create and return a ResearchDecision object using model_validate
                decision = ResearchDecision.model_validate(json_response)
                
                self.logger.info(f"Decision: {decision.is_complete}, Reasoning: {decision.reasoning[:100]}...")
                return decision
                
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse API response as JSON: {str(e)}"
                self.logger.error(error_msg)
                raise DecisionModuleError(error_msg)
            except Exception as e:
                error_msg = f"Error processing API response: {str(e)}"
                self.logger.error(error_msg)
                raise DecisionModuleError(error_msg)
                
        except DecisionModuleError:
            # Re-raise DecisionModuleError to be handled by caller
            raise
        except Exception as e:
            # Catch any other unexpected errors
            error_msg = f"Unexpected error in decision module: {str(e)}"
            self.logger.error(error_msg)
            raise DecisionModuleError(error_msg)
