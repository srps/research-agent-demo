from openai import OpenAI
import json
import logging
from .models import ResearchPlan

class ResearchPlannerError(Exception):
    """Custom exception for ResearchPlanner errors"""
    pass

class ResearchPlanner:
    """Generates a structured research plan for a given topic using an LLM."""
    
    def __init__(self):
        """Initialize the research planner."""
        self.logger = logging.getLogger(__name__)
    
    def create_plan(self, topic, api_key):
        """Create a research plan with topics and questions for the given topic.
        
        Args:
            topic (str): The research topic to create a plan for
            api_key (str): OpenAI API key
            
        Returns:
            ResearchPlan: A validated research plan with topics and questions
            
        Raises:
            ResearchPlannerError: If the plan creation fails due to API errors or invalid responses
        """
        # Initialize the OpenAI client with the API key
        client = OpenAI(api_key=api_key)    
        
        # Create a prompt for the LLM
        prompt = f"""Develop a detailed research plan for the topic: '{topic}', focusing on the following aspects to facilitate research and producing a report on the topic.

        The research plan should:
        1. Break down the topic into 5-7 key subtopics to investigate
        2. For each subtopic, provide 2-3 specific questions to research
        3. Arrange these in a logical order, from foundational concepts to more specific aspects
        4. Focus on factual, informative aspects that would be useful for a research report
        5. Ensure each question is specific enough to be used as a search query
        """
        
        self.logger.info(f"Sending research plan request for topic: {topic}")
        self.logger.debug(f"Full prompt: {prompt}")
        
        try:
            import time
            start_time = time.time()
            
            # Log the request parameters
            self.logger.debug(f"Sending request to OpenAI API with prompt: {prompt}")
            
            # Call the OpenAI API using the responses endpoint with JSON schema
            response = client.responses.create(
                model="o3-mini",
                input=[
                    {
                        "role": "developer",
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
                        "name": "research_plan",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "topics": {
                                    "type": "array",
                                    "description": "A list of research topics to investigate",
                                    "items": {
                                        "$ref": "#/$defs/research_topic"
                                    }
                                }
                            },
                            "required": [
                                "topics"
                            ],
                            "additionalProperties": False,
                            "$defs": {
                                "research_topic": {
                                    "type": "object",
                                    "description": "Represents a single research topic with related questions.",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "The title of the research topic"
                                        },
                                        "questions": {
                                            "type": "array",
                                            "description": "A list of questions related to the research topic",
                                            "items": {
                                                "type": "string"
                                            }
                                        }
                                    },
                                    "required": [
                                        "title",
                                        "questions"
                                    ],
                                    "additionalProperties": False
                                }
                            }
                        }
                    }
                },
                reasoning={
                    "effort": "medium"
                },
                tools=[],
                store=True
            )
            
            # Calculate and log response time
            response_time = time.time() - start_time
            self.logger.info(f"Successfully received research plan response in {response_time:.2f} seconds")
            
            # Check for API errors in the response
            if response.error:
                error_msg = f"API Error ({response.error.code}): {response.error.message}"
                self.logger.error(error_msg)
                raise ResearchPlannerError(error_msg)
            
            # Log detailed response information
            json_response = json.loads(response.output_text)
            self.logger.debug("OpenAI API Response Details:")
            self.logger.debug(f"Raw response: {response}")
            self.logger.debug(f"Response ID: {response.id if hasattr(response, 'id') else 'N/A'}")
            self.logger.debug(f"Model used: {response.model if hasattr(response, 'model') else 'N/A'}")
            self.logger.debug(f"Response created: {response.created if hasattr(response, 'created') else 'N/A'}")
            
            # Extract the research plan directly from the JSON response
            research_plan = ResearchPlan.model_validate(json_response)
            self.logger.debug(f"Validated research plan: {research_plan.dict()}")
            return research_plan
            
        except Exception as e:
            self.logger.error(f"Error creating research plan: {str(e)}")
            raise ResearchPlannerError(str(e))
