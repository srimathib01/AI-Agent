import os
from groq import Groq
import pandas as pd
from typing import List, Dict
import json

class LLMProcessor:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.model = "llama3-8b-8192"

    def process_results(self, results: List[Dict], query_template: str) -> pd.DataFrame:
        """
        Process search results with improved prompt engineering and result handling
        """
        extracted_data = []

        for result in results:
            if not result.get('search_results') or result.get('error'):
                extracted_data.append({
                    "entity": result['entity'],
                    "extracted_info": "Not found",
                    "confidence": 0.0
                })
                continue

            processed_result = self._process_single_result(result, query_template)
            extracted_data.append(processed_result)

        return pd.DataFrame(extracted_data)

    def _process_single_result(self, result: Dict, query_template: str) -> Dict:
        """
        Process a single result with enhanced prompt engineering
        """
        
        formatted_results = self._format_search_results(result['search_results'])
        
       
        prompt = self._construct_prompt(result['entity'], query_template, formatted_results)

        try:
            response = self._get_llm_response(prompt)
            
            
            cleaned_response = self._validate_response(response, result['entity'])
            return cleaned_response

        except Exception as e:
            return {
                "entity": result['entity'],
                "extracted_info": "Error in processing",
                "confidence": 0.0,
                "error": str(e)
            }

    def _format_search_results(self, results: List[Dict]) -> str:
        """
        Format search results for better prompt context
        """
        if isinstance(results, str):
            return results
            
        formatted = []
        for idx, result in enumerate(results, 1):
            formatted.append(f"Result {idx}:\n"
                           f"Title: {result.get('title', '')}\n"
                           f"Snippet: {result.get('snippet', '')}\n"
                           f"URL: {result.get('link', '')}\n")
        
        return "\n".join(formatted)

    def _construct_prompt(self, entity: str, query_template: str, formatted_results: str) -> str:
        """
        Construct an optimized prompt for better extraction
        """
        return f"""TASK: Extract specific information from web search results for {entity}.

QUERY: {query_template.format(entity=entity)}

INSTRUCTIONS:
1. Analyze the search results below
2. Extract ONLY the information that directly answers the query
3. Provide the answer in a single, concise line
4. If the specific information is not found, respond with "Not found"
5. Do not include any explanations or additional context

SEARCH RESULTS:
{formatted_results}

ANSWER:"""

    def _get_llm_response(self, prompt: str) -> str:
        """
        Get response from LLM with optimized parameters
        """
        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a precise information extractor. Provide only the exact information requested without any additional text or context."},
                {"role": "user", "content": prompt}
            ],
            model=self.model,
            temperature=0.1, 
            max_tokens=100,
            top_p=0.95,
            frequency_penalty=0.5,  
            presence_penalty=0.5,   
            stream=False
        )
        
        return chat_completion.choices[0].message.content.strip()

    def _validate_response(self, response: str, entity: str) -> Dict:
        """
        Validate and clean the LLM response
        """
       
        cleaned_response = response.split('\n')[0].strip()
        
       
        prefixes_to_remove = [
            "Answer:", "Response:", "Result:", 
            f"{entity}:", "The answer is:", "Information:"
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned_response.startswith(prefix):
                cleaned_response = cleaned_response[len(prefix):].strip()

       
        confidence = 1.0 if cleaned_response.lower() != "not found" else 0.0

        return {
            "entity": entity,
            "extracted_info": cleaned_response,
            "confidence": confidence
        }
