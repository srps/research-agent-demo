from openai import OpenAI
import logging
from typing import List, Dict

from research_agent.models import SearchAnnotation, SearchResponse, SearchResult, SearchContext


class WebSearchAgent:
	"""Handles web searches and summarization of search results."""

	def __init__(self):
		"""Initialize the web search module."""
		self.logger = logging.getLogger(__name__)

	def search(self, query: str, api_key: str, context: SearchContext = None) -> SearchResponse:
		"""Execute a web search for the given query.

		Args:
		    query (str): The search query
		    api_key (str): OpenAI API key
		    context (SearchContext, optional): Research context for more focused searching

		Returns:
		    SearchResponse: Object containing search results and metadata
		"""
		client = OpenAI(api_key=api_key)

		# Build a contextualized query
		contextualized_query = query

		# Enhance query with research topic and theme if available
		if context:
			# Add main research topic if available
			contextualized_query = (
				f'[Research on: {context.research_topic}] {contextualized_query}'
			)

			# Add research theme or subtopic if available
			if context.current_subtopic:
				contextualized_query = (
					f'{contextualized_query} [Subtopic: {context.current_subtopic}]'
				)

		# Log the search request with the enhanced query
		self.logger.debug(f'Executing web search for contextualized query: {contextualized_query}')

		import time

		start_time = time.time()

		# Execute the search using OpenAI's Responses API with web search tool
		response = client.responses.create(
			model='gpt-4o-mini',
			tools=[{'type': 'web_search_preview'}],
			input=f'Search for information about: {contextualized_query}',
		)

		# Calculate and log response time
		response_time = time.time() - start_time
		self.logger.info(f'Received search response in {response_time:.2f} seconds')

		# Log detailed response information
		self.logger.debug('OpenAI API Search Response Details:')
		self.logger.debug(f'Raw response: {response}')
		self.logger.debug(f'Response ID: {response.id if hasattr(response, "id") else "N/A"}')
		self.logger.debug(f'Model used: {response.model if hasattr(response, "model") else "N/A"}')
		self.logger.debug(
			f'Response created: {response.created if hasattr(response, "created") else "N/A"}'
		)

		# Extract the search results
		search_results = []

		# Process the response to extract search results
		for output_item in response.output:
			if output_item.type == 'message' and hasattr(output_item, 'content'):
				for content_item in output_item.content:
					if content_item.type == 'output_text' and hasattr(content_item, 'annotations'):
						# Extract citations as search results
						for annotation in content_item.annotations:
							if annotation.type == 'url_citation':
								# Extract the text that references this citation
								citation_text = content_item.text[
									annotation.start_index : annotation.end_index
								]

								search_results.append(
									SearchResult(
										title=annotation.title or 'Web Search Result',
										link=annotation.url,
										snippet=citation_text,
										annotation=SearchAnnotation(
											start_index=annotation.start_index,
											end_index=annotation.end_index,
											type=annotation.type,
										),
									)
								)

		# If no search results were found in annotations, create a generic one
		if not search_results and response.output:
			for output_item in response.output:
				if output_item.type == 'message' and hasattr(output_item, 'content'):
					for content_item in output_item.content:
						if content_item.type == 'output_text':
							search_results.append(
								SearchResult(
									title='OpenAI Web Search Result',
									link='',
									snippet=content_item.text,
								)
							)

		return SearchResponse(
			query=query,
			results=search_results,
			context=context,
		)

	def summarize(
		self,
		search_results: List[SearchResult],
		query: str,
		api_key: str,
		context: SearchContext = None,
	) -> str:
		"""Summarize search results.

		Args:
		    search_results (list): List of search results
		    query (str): The original query
		    api_key (str): OpenAI API key
		    context (SearchContext, optional): Research context for better summarization

		Returns:
		    str: A summary text
		"""
		# Initialize the OpenAI client
		client = OpenAI(api_key=api_key)

		# Format the search results for the prompt
		formatted_results = ''
		# Create a citation mapping for reference
		citation_references = {}
		# Import datetime here to avoid potential issues
		from datetime import datetime

		for i, result in enumerate(search_results):
			# Create a citation reference number for this result
			citation_num = i + 1
			citation_key = f'[{citation_num}]'

			# Store the citation information
			citation_references[citation_key] = {
				'title': result.title,
				'url': result.link,
				'snippet': result.snippet,
				'accessed_date': result.accessed_date,
			}

			# Format the result for the prompt
			formatted_results += f'Result {citation_num} {citation_key}:\n'
			formatted_results += f'Title: {result.title}\n'
			formatted_results += f'URL: {result.link}\n'
			formatted_results += f'Snippet: {result.snippet}\n\n'

		# Add context to summarization prompt if available
		context_prompt = ''

		# Use the provided SearchContext
		search_context = context

		if search_context:
			context_elements = []

			# Add main research topic context
			context_elements.append(f'Main research topic: {search_context.research_topic}')

			# Add current subtopic or theme context if available
			if search_context.current_subtopic:
				context_elements.append(f'Current subtopic: {search_context.current_subtopic}')

			# Add iteration information if available
			if search_context.iteration is not None:
				context_elements.append(f'Research iteration: {search_context.iteration + 1}')

			# Combine all context elements
			if context_elements:
				context_prompt = '\nResearch Context:\n- ' + '\n- '.join(context_elements)

		# Create a formatted citation guide
		citation_guide = '\n\nCitations:\n'
		for key, citation in citation_references.items():
			citation_guide += f'{key} {citation["title"]}. {citation["url"]}\n'

		# Create input text for the response API with explicit citation instructions
		input_text = f"""I'm researching the following topic: '{query}'
        
        Here are some search results I found:{context_prompt}
        
        {formatted_results}
        
        Please provide a comprehensive summary of the key information from these search results that's relevant to my research topic. 
        Include important facts, definitions, and insights. 
        Organize the information logically and make it easy to understand.
        If there are conflicting viewpoints, please note them.
        Focus particularly on addressing any gaps or questions raised in the previous research context.
        
        IMPORTANT: When referencing information from the search results, include the citation number in square brackets [X] after the relevant information. 
        For example: "According to recent studies, AI has significant impacts on healthcare [2]."
        
        Your summary should be in Markdown format and include a bibliography section at the end listing all the sources used.
        {citation_guide}
        """

		# Call the OpenAI API using the responses endpoint
		response = client.responses.create(
			model='o3-mini',
			input=[
				{
					'role': 'developer',
					'content': [
						{
							'type': 'input_text',
							'text': 'You are a research assistant that summarizes web search results into clear, concise, and informative summaries with proper citations.',
						}
					],
				},
				{'role': 'user', 'content': [{'type': 'input_text', 'text': input_text}]},
			],
			text={'format': {'type': 'text'}},
			reasoning={'effort': 'medium'},
			tools=[],
			store=True,
		)

		# Log response details
		self.logger.debug('OpenAI API Response Details:')
		self.logger.debug(f'Raw response: {response}')
		self.logger.debug(f'Response ID: {response.id if hasattr(response, "id") else "N/A"}')
		self.logger.debug(f'Model used: {response.model if hasattr(response, "model") else "N/A"}')

		# Extract the summary from the response
		summary = ''

		# Extract the markdown text from the response
		for output_item in response.output:
			if output_item.type == 'message' and hasattr(output_item, 'content'):
				for content_item in output_item.content:
					if content_item.type == 'output_text':
						summary += content_item.text

		# # Process the summary to extract citation references
		# # Look for citation patterns like [1], [2], etc.
		# import re
		# citation_pattern = r'\[(\d+)\]'
		# citation_matches = re.finditer(citation_pattern, summary)

		# # Create annotations from the citation references
		# for match in citation_matches:
		# 	citation_num = int(match.group(1))
		# 	citation_key = f'[{citation_num}]'

		# 	# Find the corresponding citation in our references
		# 	if citation_num <= len(search_results):
		# 		result = search_results[citation_num - 1]

		# 		# Create an annotation for this citation
		# 		annotations.append({
		# 			'id': f'citation_{citation_num}',
		# 			'title': result.get('title', 'Web Search Result'),
		# 			'url': result.get('link', ''),
		# 			'snippet': result.get('snippet', ''),
		# 			'accessed_date': result.get('accessed_date', datetime.now()),
		# 			# We don't have exact positions in the text, but we have the citation marker
		# 			'annotation': {
		# 				'start_index': match.start(),
		# 				'end_index': match.end(),
		# 				'type': 'citation',
		# 			},
		# 		})

		# Return both the summary and the annotations
		return summary.strip()
