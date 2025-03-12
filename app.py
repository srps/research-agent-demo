import os
import streamlit as st
from dotenv import load_dotenv
from markdown import markdown
from datetime import datetime

# Import our custom modules
from research_agent.planner import ResearchPlanner, ResearchPlannerError
from research_agent.search import WebSearchModule
from research_agent.decision import DecisionModule, DecisionModuleError
from research_agent.report import ReportGenerator, ReportGeneratorError
import logging

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(page_title="Research Agent", layout="wide")
st.title("Research Agent")

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
if 'max_iterations' not in st.session_state:
    st.session_state.max_iterations = 5  # Maximum research iterations to prevent infinite loops
if 'research_context' not in st.session_state:
    st.session_state.research_context = {}

# Initialize our agent components
planner = ResearchPlanner()
search_module = WebSearchModule()
decision_module = DecisionModule()
report_generator = ReportGenerator()

# Sidebar for API key input
with st.sidebar:
    st.header("Configuration")
    openai_api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    
    if st.button("Reset Research"):
        st.session_state.research_plan = None
        st.session_state.research_summaries = []
        st.session_state.final_report = None
        st.session_state.research_complete = False
        st.session_state.current_step = 0
        st.session_state.error_message = None
        st.session_state.previous_gaps = []
        st.session_state.gap_questions = []
        st.session_state.iteration_count = 0
        st.rerun()

# Display any error messages
if st.session_state.error_message:
    st.error(st.session_state.error_message)
    # Clear the error message after displaying it
    st.session_state.error_message = None

# Main interface
research_topic = st.text_input("Enter a research topic:", key="topic_input")

if st.button("Start Research") and research_topic:
    # Check if OpenAI API key is provided
    if not openai_api_key:
        st.error("Please provide your OpenAI API key in the sidebar.")
    else:
        try:
            with st.spinner("Creating research plan..."):
                # Generate research plan
                st.session_state.research_plan = planner.create_plan(research_topic, openai_api_key)
                st.session_state.research_summaries = []
                st.session_state.final_report = None
                st.session_state.research_complete = False
                st.session_state.current_step = 0
                st.session_state.previous_gaps = []
                st.session_state.gap_questions = []
                st.session_state.iteration_count = 0
        except ResearchPlannerError as e:
            st.session_state.error_message = f"Failed to create research plan: {str(e)}"
            st.session_state.research_plan = None
        except Exception as e:
            st.session_state.error_message = f"An unexpected error occurred: {str(e)}"
            st.session_state.research_plan = None
        st.rerun()

# Display research plan if available
if st.session_state.research_plan:
    st.subheader("Research Plan")
    for i, topic in enumerate(st.session_state.research_plan.topics):
        with st.expander(f"Topic {i+1}: {topic.title}"):
            for j, question in enumerate(topic.questions):
                st.write(f"{j+1}. {question}")
    
    # Research progress
    if not st.session_state.research_complete or (st.session_state.research_complete and not st.session_state.final_report):
        # Display current research gaps
        if 'research_context' in st.session_state and st.session_state.research_context.get('latest_decision'):
            latest_decision = st.session_state.research_context['latest_decision']
            if latest_decision.get('gaps'):
                st.subheader("Current Research Gaps")
                with st.expander("View identified gaps that need further research"):
                    for i, gap in enumerate(latest_decision['gaps'], 1):
                        st.markdown(f"**{i}.** {gap}")
                    if latest_decision.get('reasoning'):
                        st.markdown("---")
                        st.markdown("**Decision Reasoning:**")
                        st.markdown(latest_decision['reasoning'])
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Continue Research"):
                        try:
                            while (not st.session_state.research_complete and 
                                   st.session_state.current_iteration < st.session_state.max_iterations):
                                
                                # Update progress
                                progress_text = f"Research Iteration {st.session_state.current_iteration + 1}/{st.session_state.max_iterations}"
                                progress_bar = st.progress(0)
                                status_container = st.empty()
                                
                                # Initialize or update research queue
                                if not st.session_state.research_queue:
                                    # Get all initial questions from research plan
                                    for topic in st.session_state.research_plan.topics:
                                        for question in topic.questions:
                                            st.session_state.research_queue.append({
                                                'topic': topic.title,
                                                'question': question,
                                                'priority': 1,  # Default priority
                                                'iteration': st.session_state.current_iteration
                                            })
                                
                                # Process research queue
                                total_tasks = len(st.session_state.research_queue)
                                for task_index, task in enumerate(st.session_state.research_queue[:]):
                                    # Update progress
                                    progress = (task_index + 1) / total_tasks
                                    progress_bar.progress(progress)
                                    status_container.text(f"{progress_text} - Researching: {task['question']}")
                                    
                                    current_task = f"{task['topic']}: {task['question']}"
                                    
                                    with st.spinner(f"Researching: {current_task}"):
                                        # Perform research
                                        search_results = search_module.search(
                                            task['question'],
                                            openai_api_key,
                                            context=st.session_state.research_context
                                        )
                                        
                                        # Summarize findings
                                        summary = search_module.summarize(
                                            search_results,
                                            task['question'],
                                            openai_api_key,
                                            context=st.session_state.research_context
                                        )
                                        
                                        # Add citations
                                        citations = [{
                                            "title": result["title"],
                                            "url": result["link"],
                                            "snippet": result["snippet"],
                                            "accessed_date": datetime.now().isoformat()
                                        } for result in search_results]
                                        
                                        # Store research results
                                        st.session_state.research_summaries.append({
                                            "task": current_task,
                                            "summary": summary,
                                            "citations": citations,
                                            "iteration": st.session_state.current_iteration
                                        })
                                    
                                    # Remove completed task from queue
                                    st.session_state.research_queue.remove(task)
                                
                                # Evaluate research completion
                                try:
                                    decision = decision_module.is_research_complete(
                                        st.session_state.research_summaries,
                                        research_topic,
                                        openai_api_key
                                    )
                                    
                                    # Update research context with latest findings
                                    st.session_state.research_context.update({
                                        'latest_decision': decision,
                                        'total_summaries': len(st.session_state.research_summaries),
                                        'current_iteration': st.session_state.current_iteration
                                    })
                                    
                                    if decision.is_complete:
                                        st.session_state.research_complete = True
                                        status_container.text("Research complete! Generating final report...")
                                        
                                        # Generate final report
                                        with st.spinner("Generating final report..."):
                                            st.session_state.final_report = report_generator.generate_report(
                                                research_topic,
                                                st.session_state.research_plan,
                                                st.session_state.research_summaries,
                                                openai_api_key
                                            )
                                        break
                                    else:
                                        # Add new research tasks based on gaps
                                        if decision.gaps:
                                            for gap in decision.gaps:
                                                # Check if this gap is already in the queue
                                                if not any(task['question'] == gap for task in st.session_state.research_queue):
                                                    st.session_state.research_queue.append({
                                                        'topic': f"Gap Research (Iteration {st.session_state.current_iteration + 1})",
                                                        'question': gap,
                                                        'priority': 2,  # Higher priority for gap-filling research
                                                        'iteration': st.session_state.current_iteration + 1
                                                    })
                                    
                                    # Sort queue by priority (higher priority first)
                                    st.session_state.research_queue.sort(key=lambda x: (-x['priority'], x['iteration']))
                                    
                                    # Increment iteration counter
                                    st.session_state.current_iteration += 1
                                    
                                    # Update progress display
                                    status_container.text(f"Starting iteration {st.session_state.current_iteration + 1}...")
                                
                                except DecisionModuleError as e:
                                    st.error(f"Error evaluating research completion: {str(e)}")
                                    break
                                
                                # Check if we've reached max iterations
                                if st.session_state.current_iteration >= st.session_state.max_iterations:
                                    st.warning(f"Reached maximum research iterations ({st.session_state.max_iterations}). Some gaps may remain.")
                                    st.session_state.research_complete = True
                                
                                # Force UI update
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"Error during research process: {str(e)}")
                            st.session_state.error_message = str(e)
                            st.rerun()
                with col2:
                    if st.button("Generate Report Now"):
                        try:
                            if not openai_api_key:
                                st.error("Please provide your OpenAI API key in the sidebar.")
                                st.rerun()
                            
                            with st.spinner("Generating final report with current findings..."):
                                try:
                                    st.session_state.final_report = report_generator.generate_report(
                                        research_topic,
                                        st.session_state.research_plan,
                                        st.session_state.research_summaries,
                                        openai_api_key
                                    )
                                    st.success("Report generated successfully!")
                                    st.session_state.research_complete = True  # Only set to True after successful generation
                                    st.rerun()
                                except ReportGeneratorError as e:
                                    st.error(f"Failed to generate report: {str(e)}")
                                    st.session_state.final_report = None
                                    st.session_state.error_message = str(e)
                                    st.rerun()
                        except Exception as e:
                            st.error(f"An unexpected error occurred: {str(e)}")
                            st.session_state.final_report = None
                            st.session_state.error_message = str(e)

    # Update the research progress display
    if st.session_state.research_summaries:
        st.subheader("Research Progress")
        
        # Group summaries by iteration
        summaries_by_iteration = {}
        for summary in st.session_state.research_summaries:
            iteration = summary.get('iteration', 0)
            if iteration not in summaries_by_iteration:
                summaries_by_iteration[iteration] = []
            summaries_by_iteration[iteration].append(summary)
        
        # Display summaries grouped by iteration
        for iteration in sorted(summaries_by_iteration.keys()):
            st.markdown(f"**Iteration {iteration + 1}**")
            for i, summary in enumerate(summaries_by_iteration[iteration]):
                with st.expander(f"{summary['task']}"):
                    st.write(summary['summary'])
                    if summary['citations']:
                        st.markdown("**Sources:**")
                        for citation in summary['citations']:
                            st.markdown(f"- [{citation['title']}]({citation['url']})")

    # Display final report
    if st.session_state.final_report:
        st.subheader("Final Research Report")
        st.markdown(st.session_state.final_report)

# Footer
st.markdown("---")
st.markdown("Research Agent Demo - Powered by OpenAI with integrated web search")
