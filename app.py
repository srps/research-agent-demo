import os
import time
import streamlit as st
from dotenv import load_dotenv

# Import our custom modules
from research_agent.planner import ResearchPlannerAgent, ResearchPlannerError
from research_agent.search import WebSearchAgent
from research_agent.decision import DecisionAgent, DecisionModuleError
from research_agent.report import ReportGeneratorAgent, ReportGeneratorError
from research_agent.triage import TriageAgent, TriageAgentError

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(page_title='Research Agent', layout='wide')
st.title('Research Agent Demo')
st.header('Powered by OpenAI Responses API with web search')

# Initialize session state variables if they don't exist
if 'research_plan' not in st.session_state:
	st.session_state.research_plan = None
if 'research_summaries' not in st.session_state:
	st.session_state.research_summaries = []
if 'final_report' not in st.session_state:
	st.session_state.final_report = None
if 'research_complete' not in st.session_state:
	st.session_state.research_complete = False
if 'current_step' not in st.session_state:
	st.session_state.current_step = 0
if 'error_message' not in st.session_state:
	st.session_state.error_message = None
if 'previous_gaps' not in st.session_state:
	st.session_state.previous_gaps = []
if 'gap_questions' not in st.session_state:
	st.session_state.gap_questions = []
if 'iteration_count' not in st.session_state:
	st.session_state.iteration_count = 0
if 'max_iterations' not in st.session_state:
	st.session_state.max_iterations = 3  # Maximum number of gap-filling iterations
if 'active_research_queue' not in st.session_state:
	st.session_state.active_research_queue = []
if 'current_research_context' not in st.session_state:
	st.session_state.current_research_context = None
if 'research_queue' not in st.session_state:
	st.session_state.research_queue = []
if 'current_iteration' not in st.session_state:
	st.session_state.current_iteration = 0
if 'research_context' not in st.session_state:
	st.session_state.research_context = {}
if 'conversation_history' not in st.session_state:
	st.session_state.conversation_history = []
if 'triage_status' not in st.session_state:
	st.session_state.triage_status = None
if 'skip_gaps' not in st.session_state:
	st.session_state.skip_gaps = False

# Initialize our agent components
planner = ResearchPlannerAgent()
search_module = WebSearchAgent()
decision_module = DecisionAgent()
report_generator = ReportGeneratorAgent()
triage_agent = TriageAgent()

# Sidebar for API key input and display controls
with st.sidebar:
	st.header('Configuration')
	openai_api_key = st.text_input(
		'OpenAI API Key', type='password', value=os.getenv('OPENAI_API_KEY', '')
	)

	st.header('Display Settings')
	# Initialize display settings in session state if they don't exist
	if 'show_research_plan' not in st.session_state:
		st.session_state.show_research_plan = True
	if 'show_research_progress' not in st.session_state:
		st.session_state.show_research_progress = True

	# Create callback functions for the toggles
	def toggle_research_plan():
		st.session_state.show_research_plan = not st.session_state.show_research_plan

	def toggle_research_progress():
		st.session_state.show_research_progress = not st.session_state.show_research_progress

	# Use buttons instead of toggles for more reliable state management
	if st.button(
		'Research Plan: ' + ('Shown ✓' if st.session_state.show_research_plan else 'Hidden ✗'),
		on_click=toggle_research_plan,
		key='research_plan_toggle',
	):
		pass

	if st.button(
		'Research Progress: '
		+ ('Shown ✓' if st.session_state.show_research_progress else 'Hidden ✗'),
		on_click=toggle_research_progress,
		key='research_progress_toggle',
	):
		pass

	# Add a divider before the control buttons
	st.markdown('---')
	st.header('Research Settings')
	# Add toggle for skipping gaps
	st.session_state.skip_gaps = st.toggle(
		'Skip Gap Analysis',
		value=st.session_state.skip_gaps,
		help='When enabled, the research will proceed without gap analysis'
	)
	
	st.markdown('---')
	st.header('Research Controls')
	
	if st.button('Reset Research'):
		st.session_state.research_plan = None
		st.session_state.research_summaries = []
		st.session_state.final_report = None
		st.session_state.research_complete = False
		st.session_state.current_step = 0
		st.session_state.error_message = None
		st.session_state.previous_gaps = []
		st.session_state.gap_questions = []
		st.session_state.iteration_count = 0
		st.session_state.conversation_history = []
		st.session_state.triage_status = None
		st.session_state.triage_decision = None
		st.session_state.research_topic = None
		st.session_state.research_context = {}
		# Add missing state resets
		st.session_state.active_research_queue = []
		st.session_state.current_research_context = None
		st.session_state.research_queue = []
		st.session_state.current_iteration = 0
		st.rerun()

	# Add the Skip Gaps button, only show it when research is in progress
	if (st.session_state.research_plan and 
		st.session_state.research_summaries and 
		not st.session_state.research_complete):
		
		if st.button('Skip Gaps & Generate Report'):
			try:
				if not openai_api_key:
					st.error('Please provide your OpenAI API key in the sidebar.')
					st.rerun()

				with st.spinner('Generating final report with current findings...'):
					st.session_state.final_report = report_generator.generate_report(
						st.session_state.research_topic,
						st.session_state.research_plan,
						st.session_state.research_summaries,
						openai_api_key,
					)
					st.session_state.research_complete = True
					st.session_state.research_queue = []  # Clear the research queue
					st.success('Report generated successfully!')
					st.rerun()
			except Exception as e:
				st.error(f'Error generating report: {str(e)}')
				st.session_state.error_message = str(e)
				st.rerun()

# Display any error messages
if st.session_state.error_message:
	st.error(st.session_state.error_message)
	# Clear the error message after displaying it
	st.session_state.error_message = None

# Main interface
st.markdown("Enter a research topic and click 'Start Research' to begin.")
research_topic = st.text_input('Enter a research topic:', key='topic_input')

if st.session_state.triage_status == 'invalid':
	st.error(f'Cannot proceed with research: {st.session_state.triage_decision.reasoning}')

if st.session_state.triage_status == 'needs_clarification':
	# Display the clarification question in markdown format
	st.markdown('### Clarification Needed')
	st.markdown(st.session_state.triage_decision.clarification_question)

	# Create a dedicated input field for clarification
	clarification_response = st.text_input('Your clarification:', key='clarification_input')
	submit_button = st.button('Submit Clarification')

	if submit_button and clarification_response:
		if not openai_api_key:
			st.error('Please provide your OpenAI API key in the sidebar.')
		else:
			try:
				# Add user's clarification to conversation history
				st.session_state.conversation_history.append(
					{'role': 'user', 'content': clarification_response}
				)

				# Re-triage with the updated conversation
				with st.spinner('Processing your clarification...'):
					triage_decision = triage_agent.triage_query(
						st.session_state.research_topic,
						openai_api_key,
						st.session_state.conversation_history,
					)
					
					# Store the full triage decision and status
					st.session_state.triage_decision = triage_decision
					st.session_state.triage_status = triage_decision.status

					if triage_decision.status == 'valid':
						with st.spinner('Creating research plan...'):
							# Generate research plan with original topic and clarification
							original_topic = st.session_state.conversation_history[0]['content']
							st.session_state.research_plan = planner.create_plan(
								original_topic, openai_api_key, clarification=clarification_response
							)
							st.session_state.research_summaries = []
							st.session_state.final_report = None
							st.session_state.research_complete = False
							st.session_state.current_step = 0
							st.session_state.previous_gaps = []
							st.session_state.gap_questions = []
							st.session_state.iteration_count = 0
					elif triage_decision.status == 'invalid':
						# Clear any existing research state
						st.session_state.research_plan = None
						st.session_state.conversation_history = []
			except TriageAgentError as e:
				st.session_state.error_message = f'Error processing your request: {str(e)}'
			except ResearchPlannerError as e:
				st.session_state.error_message = f'Failed to create research plan: {str(e)}'
				st.session_state.research_plan = None
			except Exception as e:
				st.session_state.error_message = f'An unexpected error occurred: {str(e)}'
				st.session_state.research_plan = None
			st.rerun()
else:
	if st.button('Start Research') and research_topic:
		st.session_state.research_topic = research_topic
		# Check if OpenAI API key is provided
		if not openai_api_key:
			st.error('Please provide your OpenAI API key in the sidebar.')
		else:
			try:
				# First, triage the user's query
				with st.spinner('Analyzing your request...'):
					# Add the query to conversation history
					st.session_state.conversation_history = [
						{'role': 'user', 'content': research_topic}
					]

					# Triage the query
					triage_decision = triage_agent.triage_query(research_topic, openai_api_key)
					
					# Store the full triage decision and status
					st.session_state.triage_decision = triage_decision
					st.session_state.triage_status = triage_decision.status

					if triage_decision.status == 'valid':
						with st.spinner('Creating research plan...'):
							# Generate research plan
							st.session_state.research_plan = planner.create_plan(
								research_topic, openai_api_key
							)
							st.session_state.research_summaries = []
							st.session_state.final_report = None
							st.session_state.research_complete = False
							st.session_state.current_step = 0
							st.session_state.previous_gaps = []
							st.session_state.gap_questions = []
							st.session_state.iteration_count = 0
			except TriageAgentError as e:
				st.session_state.error_message = f'Error processing your request: {str(e)}'
			except ResearchPlannerError as e:
				st.session_state.error_message = f'Failed to create research plan: {str(e)}'
				st.session_state.research_plan = None
			except Exception as e:
				st.session_state.error_message = f'An unexpected error occurred: {str(e)}'
				st.session_state.research_plan = None
			st.rerun()

# Display research plan if available and enabled
if st.session_state.research_plan:
	if st.session_state.show_research_plan:
		st.subheader('Research Plan')
		for i, topic in enumerate(st.session_state.research_plan.topics):
			with st.expander(f'Topic {i + 1}: {topic.title}'):
				for j, question in enumerate(topic.questions):
					st.write(f'{j + 1}. {question}')

	# Research control section - always show if we have a plan and research isn't complete
	if not st.session_state.research_complete:
		st.subheader('Research Controls')

		# Initialize research queue if it doesn't exist
		if not hasattr(st.session_state, 'research_queue'):
			st.session_state.research_queue = []

		# Show start research button if queue is empty and research hasn't started
		if not st.session_state.research_queue and not st.session_state.research_summaries:
			if st.button('Execute Research Plan'):
				# Initialize the research queue with all questions from the plan
				for topic in st.session_state.research_plan.topics:
					for question in topic.questions:
						st.session_state.research_queue.append(
							{
								'topic': topic.title,
								'question': question,
								'priority': 1,  # Default priority
								'iteration': 0,  # Initial iteration
							}
						)

		# Show continue research button if research is in progress
		elif st.session_state.research_queue or st.session_state.research_summaries:
			col1, col2 = st.columns(2)
			with col1:
				if st.button('Execute Research Plan'):
					# At the start of research execution, create containers for live updates
					progress_container = st.empty()
					status_container = st.empty()

					# Before the research loop starts, create a single container for latest results
					latest_results_container = st.empty()

					# Create a container for gaps display that will update in real-time
					gaps_container = st.empty()

					try:
						while (not st.session_state.research_complete 
							   and st.session_state.current_iteration < st.session_state.max_iterations):
							
							# Update progress display
							with progress_container:
								st.progress((st.session_state.current_iteration + 1) / st.session_state.max_iterations)
								
							# Process research queue
							total_tasks = len(st.session_state.research_queue)
							for task_index, task in enumerate(st.session_state.research_queue[:]):
								# Update status
								with status_container:
									st.write(f'Researching: {task["question"]} ({task_index + 1}/{total_tasks})')
								
								current_task = f'{task["topic"]}: {task["question"]}'

								with st.spinner(f'Researching: {task["question"]}'):
									# Prepare search context with only relevant information
									from research_agent.models import SearchContext
									search_context = SearchContext(
										research_topic=st.session_state.research_topic,
										current_subtopic=task['topic'],
										iteration=st.session_state.current_iteration
									)

									# Perform research
									search_response = search_module.search(
										task['question'],
										openai_api_key,
										context=search_context,
									)

									# Summarize findings
									summary = search_module.summarize(
										search_response.results,
										task['question'],
										openai_api_key,
										context=search_context,
									)

									# Add citations
									citations = [
										{
											'title': result.title,
											'url': result.link,
											'snippet': result.snippet,
											'accessed_date': result.accessed_date.isoformat(),
										}
										for result in search_response.results
									]

									# Store research results
									st.session_state.research_summaries.append(
										{
											'task': current_task,
											'summary': summary,
											'citations': citations,
											'iteration': st.session_state.current_iteration,
										}
									)

									# Update results display in real-time
									with latest_results_container:
										st.markdown("### Latest Research Results")
										latest_summary = st.session_state.research_summaries[-1]
										with st.expander(f"{latest_summary['task']} (In Progress)", expanded=True):
											st.write(latest_summary['summary'])
											if latest_summary['citations']:
												st.markdown("**Sources:**")
												for citation in latest_summary['citations']:
													st.markdown(f"- [{citation['title']}]({citation['url']})")

								# Remove completed task from queue
								st.session_state.research_queue.remove(task)

							# Evaluate research completion
							try:
								decision = decision_module.is_research_complete(
									st.session_state.research_summaries,
									st.session_state.research_topic,
									openai_api_key,
								)
								
								# If skip_gaps is enabled, clear any gaps and mark as complete
								if st.session_state.skip_gaps:
									decision.gaps = []
									decision.is_complete = True
								
							except DecisionModuleError as e:
								st.error(f'Error evaluating research completion: {str(e)}')
								break
							except Exception as e:
								st.error(f'Unexpected error during research evaluation: {str(e)}')
								break

							# Update research context with latest findings
							st.session_state.research_context.update({
								'latest_decision': decision,
								'total_summaries': len(st.session_state.research_summaries),
								'current_iteration': st.session_state.current_iteration,
							})

							# Only show gaps if not skipping
							if not st.session_state.skip_gaps:
								with gaps_container:
									if decision.gaps:
										st.markdown('### Current Research Gaps')
										for i, gap in enumerate(decision.gaps, 1):
											st.markdown(f'**{i}.** {gap}')
										if decision.reasoning:
											st.markdown('---')
											st.markdown('**Decision Reasoning:**')
											st.markdown(decision.reasoning)

							if decision.is_complete:
								st.session_state.research_complete = True
								status_container.text('Research complete! Generating final report...')

								# Generate final report
								with st.spinner('Generating final report...'):
									st.session_state.final_report = report_generator.generate_report(
										st.session_state.research_topic,
										st.session_state.research_plan,
										st.session_state.research_summaries,
										openai_api_key,
									)
								break
							else:
								# Add new research tasks based on gaps
								if decision.gaps:
									for gap in decision.gaps:
										if not any(task['question'] == gap for task in st.session_state.research_queue):
											st.session_state.research_queue.append(
												{
													'topic': f'Gap Research (Iteration {st.session_state.current_iteration + 1})',
													'question': gap,
													'priority': 2,
													'iteration': st.session_state.current_iteration + 1,
												}
											)

							# Sort queue by priority
							st.session_state.research_queue.sort(key=lambda x: (-x['priority'], x['iteration']))

							# Increment iteration counter
							st.session_state.current_iteration += 1

						# Check if we've reached max iterations
						if st.session_state.current_iteration >= st.session_state.max_iterations:
							st.warning(f'Reached maximum research iterations ({st.session_state.max_iterations}). Some gaps may remain.')
							st.session_state.research_complete = True

						# Clean up temporary containers
						progress_container.empty()
						status_container.empty()
						
						st.rerun()  # Single rerun at the end of all processing

					except Exception as e:
						st.error(f'Error during research process: {str(e)}')
						st.session_state.error_message = str(e)
						st.rerun()
			with col2:
				if st.button('Generate Report Now'):
					try:
						if not openai_api_key:
							st.error('Please provide your OpenAI API key in the sidebar.')
							st.rerun()

						with st.spinner('Generating final report with current findings...'):
							try:
								st.session_state.final_report = report_generator.generate_report(
									st.session_state.research_topic,
									st.session_state.research_plan,
									st.session_state.research_summaries,
									openai_api_key,
								)
								st.success('Report generated successfully!')
								st.session_state.research_complete = (
									True  # Only set to True after successful generation
								)
								st.rerun()
							except ReportGeneratorError as e:
								st.error(f'Failed to generate report: {str(e)}')
								st.session_state.final_report = None
								st.session_state.error_message = str(e)
								st.rerun()
					except Exception as e:
						st.error(f'An unexpected error occurred: {str(e)}')
						st.session_state.final_report = None
						st.session_state.error_message = str(e)

	# Research progress section - independent of research plan visibility
	if st.session_state.research_summaries and st.session_state.show_research_progress:
		st.subheader('Research Progress')

		# Create a container for gaps display that will update in real-time
		gaps_container = st.empty()

		# Display current research gaps if any
		if 'research_context' in st.session_state and st.session_state.research_context.get('latest_decision'):
			latest_decision = st.session_state.research_context['latest_decision']
			with gaps_container:
				if latest_decision.gaps:
					st.markdown('### Current Research Gaps')
					for i, gap in enumerate(latest_decision.gaps, 1):
						st.markdown(f'**{i}.** {gap}')
					if latest_decision.reasoning:
						st.markdown('---')
						st.markdown('**Decision Reasoning:**')
						st.markdown(latest_decision.reasoning)

		# Create a unique identifier for each summary to prevent duplicates
		# Initialize a container for summaries
		summary_container = st.container()

		# Group summaries by iteration
		summaries_by_iteration = {}
		for summary in st.session_state.research_summaries:
			iteration = summary.get('iteration', 0)
			if iteration not in summaries_by_iteration:
				summaries_by_iteration[iteration] = []
			summaries_by_iteration[iteration].append(summary)

		# Display summaries grouped by iteration
		with summary_container:
			for iteration in sorted(summaries_by_iteration.keys()):
				st.markdown(f'**Iteration {iteration + 1}**')
				for i, summary in enumerate(summaries_by_iteration[iteration]):
					# Create a unique key for each summary based on task and iteration
					summary_key = f'summary_{iteration}_{i}_{hash(summary["task"])}'
					with st.expander(f'{summary["task"]}'):
						st.write(summary['summary'])
						if summary['citations']:
							st.markdown('**Sources:**')
							for citation in summary['citations']:
								st.markdown(f'- [{citation["title"]}]({citation["url"]})')

	# Display final report if available (keep this separate)
	if st.session_state.final_report:
		st.subheader('Final Research Report')
		st.markdown(st.session_state.final_report)
