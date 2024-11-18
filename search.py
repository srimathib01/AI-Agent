import requests
from typing import List, Dict
import time

class SearchEngine:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.max_retries = 3
        self.retry_delay = 2

    def search_entities(self, entities: List[str], query_template: str,) -> List[Dict]:
        """
        Enhanced search function with retry logic and better result filtering
        """
        results = []
        
        for entity in entities:
            query = query_template.format(entity=entity)
            result = self._execute_search(entity, query)
            results.append(result)
            
            # Rate limiting to avoid API throttling
            time.sleep(1)
        
        return results

    def _execute_search(self, entity: str, query: str) -> Dict:
        """
        Execute search with retry logic and enhanced error handling
        """
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.base_url,
                    params={
                        "engine": "google",
                        "q": query,
                        "api_key": self.api_key,
                        "num": 3 
                    },
                    timeout=10
                )
                
                if response.ok:
                    return self._process_response(entity, response)
                    
                if response.status_code == 429:  # Rate limit
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    return {
                        "entity": entity,
                        "search_results": None,
                        "error": f"Request failed after {self.max_retries} attempts: {str(e)}"
                    }
                time.sleep(self.retry_delay)
                
        return {
            "entity": entity,
            "search_results": None,
            "error": f"Request failed after {self.max_retries} attempts"
        }

    def _process_response(self, entity: str, response: requests.Response) -> Dict:
        """
        Process and filter search results
        """
        try:
            data = response.json()
            organic_results = data.get("organic_results", [])
            
            filtered_results = []
            for result in organic_results:
                processed_result = {
                    "title": result.get("title"),
                    "link": result.get("link"),
                    "snippet": result.get("snippet"),  # Including snippet for better context
                    "position": result.get("position")
                }
                
                # Only include results with all required fields
                if all(processed_result.values()):
                    filtered_results.append(processed_result)
            
            return {
                "entity": entity,
                "search_results": filtered_results if filtered_results else "No relevant results found."
            }
            
        except Exception as e:
            return {
                "entity": entity,
                "search_results": None,
                "error": f"Failed to process results: {str(e)}"
            }