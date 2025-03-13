from typing import List, Optional, Dict
from typing_extensions import Annotated
from pydantic import BaseModel, Field, validator, AfterValidator
from datetime import datetime


class Citation(BaseModel):
	"""Represents a citation source for research information."""

	title: str = Field(..., description='The title of the source')
	url: str = Annotated[
		Field(..., description='The URL of the source'), AfterValidator('url_not_empty')
	]
	snippet: str = Field(..., description='The relevant text snippet from the source')
	accessed_date: datetime = Field(
		default_factory=datetime.now, description='When the source was accessed'
	)
	annotation: dict = Field(default=None, description='Annotation details for inline citation')

	def url_not_empty(v: str):
		if not v.strip():
			raise ValueError('URL cannot be empty')
		return v


class ResearchTopic(BaseModel):
	"""Represents a single research topic with related questions."""

	title: str = Annotated[
		Field(..., description='The title of the research topic'), AfterValidator('title_not_empty')
	]
	questions: List[str] = Annotated[
		Field(..., description='A list of questions related to the research topic'),
		AfterValidator('questions_not_empty'),
	]

	def title_not_empty(v: str):
		if not v.strip():
			raise ValueError('Research topic title cannot be empty')
		return v.strip()

	def questions_not_empty(v: List[str]):
		if not v:
			raise ValueError('Research topic must have at least one question')
		for i, question in enumerate(v):
			if not question.strip():
				raise ValueError(f'Question {i + 1} cannot be empty')
			v[i] = question.strip()
		return v


class ResearchPlan(BaseModel):
	"""Represents a complete research plan with multiple topics and their questions."""

	topics: List[ResearchTopic] = Annotated[
		Field(..., description='A list of research topics to investigate'),
		AfterValidator('validate_topics'),
	]

	def validate_topics(v: List[ResearchTopic]):
		if not v:
			raise ValueError('Research plan must have at least one topic')
		return v


class ResearchSummary(BaseModel):
	"""Represents a summary of research on a specific topic or question."""

	task: str = Field(..., description='The research task or question')
	summary: str = Field(..., description='The summary of the research findings')
	citations: List[Citation] = Field(
		default_factory=list, description='Citations for the sources used in this summary'
	)


class ResearchDecision(BaseModel):
	"""Represents a decision about whether research is complete, with reasoning."""

	is_complete: bool = Field(..., description='Whether the research is considered complete')
	reasoning: str = Field(..., description='Explanation of why the research is or is not complete')
	gaps: List[str] = Field(
		default_factory=list, description='Specific gaps in the research that need to be addressed'
	)


class SearchContext(BaseModel):
	"""Represents the context for a search query, focusing on research topic and subtopic."""

	research_topic: str = Field(..., description='The main research topic being investigated')
	current_subtopic: Optional[str] = Field(
		None, description='The current subtopic or theme being researched'
	)
	iteration: Optional[int] = Field(None, description='The current research iteration number')


class SearchAnnotation(BaseModel):
	"""Represents the annotation details for a search result."""

	start_index: int = Field(..., description='Starting index of the annotation in the text')
	end_index: int = Field(..., description='Ending index of the annotation in the text')
	type: str = Field(..., description='Type of the annotation (e.g., "url_citation")')


class SearchResult(BaseModel):
	"""Represents a single search result from web search."""

	title: str = Field(..., description='Title of the search result')
	link: str = Field(default='', description='URL of the search result')
	snippet: str = Field(..., description='Text snippet from the search result')
	accessed_date: datetime = Field(
		default_factory=datetime.now, description='Timestamp when the search result was retrieved'
	)
	annotation: Optional[SearchAnnotation] = Field(
		default=None, description='Annotation details for the search result'
	)


class SearchResponse(BaseModel):
	"""Represents the complete response from a web search."""

	query: str = Field(..., description='Original search query')
	results: List[SearchResult] = Field(default_factory=list, description='List of search results')
	context: Optional[SearchContext] = Field(
		default=None, description='Additional context used for the search'
	)
	timestamp: datetime = Field(
		default_factory=datetime.now, description='When the search was performed'
	)
