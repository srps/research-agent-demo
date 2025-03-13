from openai import OpenAI
import logging
import json
from typing import Optional
from pydantic import BaseModel


class TriageDecision(BaseModel):
	"""Represents a decision about a user query."""

	status: str  # 'valid', 'invalid', or 'needs_clarification'
	reasoning: str  # Explanation for the decision
	clarification_question: Optional[str] = (
		None  # Question to ask the user if clarification is needed
	)


class TriageAgentError(Exception):
	"""Custom exception for TriageAgent errors"""

	pass


class TriageAgent:
	"""Evaluates user queries to determine if they're valid research requests."""

	def __init__(self):
		"""Initialize the triage agent."""
		self.logger = logging.getLogger(__name__)
		self.conversation_history = []

	def triage_query(
		self, query: str, api_key: str, conversation_history: Optional[list] = None
	) -> TriageDecision:
		"""Evaluate a user query to determine if it's a valid research request.

		Args:
		    query (str): The user's query or request
		    api_key (str): OpenAI API key
		    conversation_history (Optional[list]): Previous conversation messages if available

		Returns:
		    TriageDecision: A decision object with status and reasoning

		Raises:
		    TriageAgentError: If there's an error with the API call or response processing
		"""
		try:
			if not api_key:
				raise TriageAgentError('OpenAI API key is required')

			if not query:
				raise TriageAgentError('User query is required')

			# Initialize the OpenAI client with the API key
			client = OpenAI(api_key=api_key)

			self.logger.debug(f'Triaging query: {query}')

			# Update conversation history if provided
			if conversation_history:
				self.conversation_history = conversation_history

			# Add the current query to the conversation history
			self.conversation_history.append({'role': 'user', 'content': query})

			# Format the conversation history for the prompt
			formatted_history = ''
			if len(self.conversation_history) > 1:  # If there's more than just the current query
				for i, message in enumerate(
					self.conversation_history[:-1]
				):  # Exclude the current query
					role = 'User' if message['role'] == 'user' else 'Assistant'
					formatted_history += f'{role}: {message["content"]}\n\n'

			# Create a prompt for the LLM
			prompt = f"""I am a research agent that helps users create comprehensive research reports on various topics.
            
            {formatted_history if formatted_history else ''}
            
            The user has just sent this query: "{query}"
            
            Evaluate whether this query is:
            1. A valid research topic that I can create a report on
            2. An invalid request (not asking for research or a report)
            3. A request that needs clarification before I can proceed
            
            A valid research topic should be a clear subject that can be researched to create a comprehensive report.
            Examples of valid topics: "The impact of artificial intelligence on healthcare", "History and evolution of renewable energy"
            
            An invalid request might be a command, a question unrelated to research, or something that doesn't make sense.
            Examples of invalid requests: "What's the weather today?", "Tell me a joke", "Send an email to John"
            
            A request needing clarification might be too vague, too broad, or ambiguous.
            Examples: "AI", "Tell me about science", "Research this topic"
            
            Please provide your assessment in the following JSON format:
            {{
                "status": "valid" or "invalid" or "needs_clarification",
                "reasoning": "Your detailed explanation of why the query falls into this category",
                "clarification_question": "If status is 'needs_clarification', provide a specific question to ask the user to clarify their request"
            }}
            """

			# Log the request
			self.logger.debug(
				f'Sending request to OpenAI API with prompt length: {len(prompt)} characters'
			)

			import time

			start_time = time.time()

			try:
				# Call the OpenAI API using the responses endpoint with JSON schema
				response = client.responses.create(
					model='gpt-4o-mini',
					input=[{'role': 'system', 'content': [{'type': 'input_text', 'text': prompt}]}],
					text={
						'format': {
							'type': 'json_schema',
							'name': 'triage_decision',
							'strict': True,
							'schema': {
								'type': 'object',
								'properties': {
									'status': {
										'type': 'string',
										'description': "The status of the user query, options are 'valid', 'invalid', or 'needs_clarification'.",
									},
									'reasoning': {
										'type': 'string',
										'description': 'Explanation for the decision.',
									},
									'clarification_question': {
										'type': 'string',
										'description': 'Question to ask the user if clarification is needed.',
									},
								},
								'required': ['status', 'reasoning', 'clarification_question'],
								'additionalProperties': False,
							},
						}
					},
					tools=[],
					store=True,
				)
			except Exception as e:
				error_msg = f'API call failed: {str(e)}'
				self.logger.error(error_msg)
				raise TriageAgentError(error_msg)

			# Calculate and log response time
			response_time = time.time() - start_time
			self.logger.info(f'Received triage response in {response_time:.2f} seconds')

			# Log detailed response information
			self.logger.debug('OpenAI API Response Details:')
			self.logger.debug(f'Raw response: {response}')

			# Check for API errors in the response
			if response.error:
				error_msg = f'API Error ({response.error.code}): {response.error.message}'
				self.logger.error(error_msg)
				raise TriageAgentError(error_msg)

			try:
				# Extract the decision from the response
				json_response = json.loads(response.output_text)
				self.logger.debug(f'Response JSON: {json_response}')

				# Create and return a TriageDecision object
				decision = TriageDecision(
					status=json_response['status'],
					reasoning=json_response['reasoning'],
					clarification_question=json_response.get('clarification_question'),
				)

				# Add the assistant's response to the conversation history
				if decision.status == 'needs_clarification' and decision.clarification_question:
					self.conversation_history.append(
						{'role': 'assistant', 'content': decision.clarification_question}
					)

				self.logger.info(
					f'Triage Decision: {decision.status}, Reasoning: {decision.reasoning[:100]}...'
				)
				return decision

			except json.JSONDecodeError as e:
				error_msg = f'Failed to parse API response as JSON: {str(e)}'
				self.logger.error(error_msg)
				raise TriageAgentError(error_msg)
			except Exception as e:
				error_msg = f'Error processing API response: {str(e)}'
				self.logger.error(error_msg)
				raise TriageAgentError(error_msg)

		except TriageAgentError:
			# Re-raise TriageAgentError to be handled by caller
			raise
		except Exception as e:
			# Catch any other unexpected errors
			error_msg = f'Unexpected error in triage agent: {str(e)}'
			self.logger.error(error_msg)
			raise TriageAgentError(error_msg)
