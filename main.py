import streamlit as st
import pandas as pd
import io
import os
from typing import List, Dict
from dotenv import load_dotenv
from search import SearchEngine
from llm_processing import LLMProcessor
from data_processing import connect_google_sheets
import time

class AIAgentApp:
    def __init__(self):
        load_dotenv()
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        
        if not self.serpapi_key or not self.groq_api_key:
            st.error("Missing API keys. Please check your .env file.")
            st.stop()
            
        self.search_engine = SearchEngine(self.serpapi_key)
        self.llm_processor = LLMProcessor(self.groq_api_key)

    def process_entity_with_retry(self, entity: str, query_template: str, max_retries: int = 3) -> Dict:
        """Process a single entity with retry logic"""
        for attempt in range(max_retries):
            try:
                # Search phase
                search_result = self.search_engine._execute_search(
                    entity, 
                    query_template.format(entity=entity)
                )
                
                if search_result.get('error'):
                    raise Exception(search_result['error'])
                
                # LLM processing phase
                processed_result = self.llm_processor._process_single_result(
                    search_result,
                    query_template
                )
                
                return processed_result
                
            except Exception as e:
                if attempt == max_retries - 1:
                    return {
                        "entity": entity,
                        "extracted_info": f"Error: {str(e)}",
                        
                    }
                time.sleep(2 ** attempt)  # Exponential backoff
                
        return {
            "entity": entity,
            "extracted_info": "Failed after all retries",
            
        }

    def process_data(self, data: pd.DataFrame, main_column: str, query_template: str):
        """Process data with improved error handling and retries"""
        try:
            # Get unique, non-empty entities
            entities = data[main_column].dropna().unique().tolist()
            if not entities:
                st.error("No valid entities found in the selected column.")
                return

            # Create containers for different types of output
            progress_container = st.container()
            results_container = st.container()
            error_container = st.container()

            with progress_container:
                st.info(f"Processing {len(entities)} unique entities...")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
            # Process entities
            results = []
            failed_entities = []
            
            for idx, entity in enumerate(entities):
                status_text.text(f"Processing: {entity}")
                
                try:
                    result = self.process_entity_with_retry(entity, query_template)
                    results.append(result)
                    
                    # If processing failed, add to failed entities list
                    if "Error" in str(result.get('extracted_info', '')):
                        failed_entities.append(entity)
                        
                except Exception as e:
                    failed_entities.append(entity)
                    results.append({
                        "entity": entity,
                        "extracted_info": f"Error: {str(e)}",
                       
                    })
                
                # Update progress
                progress_bar.progress((idx + 1) / len(entities))
            
            # Create results DataFrame
            results_df = pd.DataFrame(results)
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Show results
            with results_container:
                st.success("Processing completed!")
                self.display_results(results_df, failed_entities)
            
        except Exception as e:
            st.error(f"An error occurred during processing: {str(e)}")

    def display_results(self, results_df: pd.DataFrame, failed_entities: List[str]):
        """Display results with improved download options and error reporting"""
        st.subheader("Results")
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Processed", len(results_df))
        with col2:
            successful = len(results_df[~results_df['extracted_info'].str.contains('Error', na=False)])
            st.metric("Successful", successful)
        with col3:
            st.metric("Failed", len(failed_entities))
        
        # Show results table
        st.dataframe(results_df, use_container_width=True)
        
        # Show failed entities if any
        if failed_entities:
            with st.expander("Show Failed Entities"):
                st.write("The following entities failed to process:")
                for entity in failed_entities:
                    st.write(f"- {entity}")
        
        # Download options
        col1, col2 = st.columns(2)
        
        # CSV download
        with col1:
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download CSV",
                csv,
                "results.csv",
                "text/csv",
                key='download-csv'
            )
        
        # Excel download
        with col2:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                results_df.to_excel(writer, sheet_name='Results', index=False)
            buffer.seek(0)
            
            st.download_button(
                "Download Excel",
                buffer,
                "results.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key='download-excel'
            )

    def run(self):
        """Main application logic"""
        st.title("AI Research Agent 🔍")
        
        # Data source selection
        data_source = st.radio(
            "Select Data Source:",
            ("Upload CSV File", "Connect to Google Sheets")
        )
        
        # Data loading
        data = None
        if data_source == "Upload CSV File":
            uploaded_file = st.file_uploader("Upload CSV File", type=["csv","xlsv"])
            if uploaded_file:
                try:
                    data = pd.read_csv(uploaded_file)
                except Exception as e:
                    st.error(f"Error reading CSV: {str(e)}")
        
        elif data_source == "Connect to Google Sheets":
            spreadsheet_id = st.text_input("Enter Google Sheets ID")
            if spreadsheet_id:
                try:
                    sheet_data = connect_google_sheets(spreadsheet_id)
                    data = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])
                except Exception as e:
                    st.error(f"Error connecting to Google Sheets: {str(e)}")
        
        if data is not None and not data.empty:
            st.write("Data Preview:", data.head())
            
            # Query configuration
            st.subheader("Configure Your Query")
            main_column = st.selectbox("Select the main column", data.columns)
            
            query_template = st.text_input(
                "Enter your query",
                placeholder="Example: What is the revenue of {entity} in 2023?"
            )
            
            if st.button("Start Process", type="primary"):
                if "{entity}" not in query_template:
                    st.error("Query must contain {entity} placeholder")
                else:
                    self.process_data(data, main_column, query_template)

if __name__ == "__main__":
    app = AIAgentApp()
    app.run()