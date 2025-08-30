"""RAG Service - Query Analysis with LLM"""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import tiktoken
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from openai.types.chat.completion_create_params import ResponseFormatJSONObject

from app.config.chroma_config import get_chroma_client
from app.config.mongodb_config import get_mongodb_client

logger = logging.getLogger(__name__)


class RAGService:
    """RAG Service for query analysis using LLM"""

    def __init__(self):
        """Initialize RAG Service with OpenAI client"""
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.client = OpenAI(api_key=self.openai_api_key)
        self.embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")

        # Load prompts from files
        self.prompt_dir = Path(__file__).parent.parent / "prompt"
        self.query_parser_prompt = self._load_prompt("query_parser_system_prompt.txt")
        self.analysis_prompt = self._load_prompt("analysis_system_prompt.txt")
        self.script_prompt_template = self._load_prompt("script_prompt.txt")

    def _load_prompt(self, filename: str) -> str:
        """
        Load prompt from file

        Args:
            filename: Prompt file name

        Returns:
            Prompt content as string
        """
        prompt_path = self.prompt_dir / filename
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading prompt file {filename}: {e}")
            raise

    def _parse_query_with_llm(self, query: str) -> Dict:
        """
        Parse user query to extract token information and time data using GPT-4o

        Args:
            query: User's natural language query

        Returns:
            Dict with extracted information:
                - token: Token symbol (e.g., "BTC", "ETH")
                - date: Date in YYYY-MM-DD format
                - original_query: Original query for semantic search
        """
        logger.info("Parsing query with GPT-4o...")

        user_prompt = f"Parse this query: {query}\n\nToday's date is: {datetime.now().strftime('%Y-%m-%d')}"

        try:
            system_message: ChatCompletionSystemMessageParam = {
                "role": "system",
                "content": self.query_parser_prompt
            }
            user_message: ChatCompletionUserMessageParam = {
                "role": "user",
                "content": user_prompt
            }

            json_format: ResponseFormatJSONObject = {"type": "json_object"}

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[system_message, user_message],
                response_format=json_format,
                temperature=0
            )

            parsed_data = json.loads(response.choices[0].message.content)
            logger.info(f"Parsed query: {parsed_data}")

            return parsed_data

        except Exception as e:
            logger.error(f"Error parsing query with LLM: {e}")
            raise

    def _search_chromadb(self, query: str, date_epoch: int, top_k: int = 5) -> List[Dict]:
        """
        Search ChromaDB for relevant news chunks

        Args:
            query: Search query (will be embedded)
            date_epoch: Target date as epoch timestamp
            top_k: Number of results to return

        Returns:
            List of relevant news chunks with metadata
        """
        logger.info(f"Searching ChromaDB for query='{query}', date_epoch={date_epoch}, top_k={top_k}")

        try:
            # Get ChromaDB collection
            chroma_client = get_chroma_client()
            collection = chroma_client.get_or_create_collection("coin_news")

            # Generate embedding for query
            query_embedding = self.embeddings_model.embed_query(query)

            # Calculate date range (start and end of day)
            # Assume date_epoch is start of day, add 86400 seconds (24 hours) for end of day
            start_epoch = date_epoch
            end_epoch = date_epoch + 86399  # 23:59:59 of the same day

            # Search with date filter using epoch timestamps
            # ChromaDB supports numeric comparisons with $gte, $lte
            # Use publish_date_epoch field which contains the numeric epoch timestamp
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={
                    "$and": [
                        {"publish_date_epoch": {"$gte": start_epoch}},
                        {"publish_date_epoch": {"$lte": end_epoch}}
                    ]
                }
            )

            # Format results
            chunks = []
            if results and results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    chunk_data = {
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else None
                    }
                    chunks.append(chunk_data)

            logger.info(f"Found {len(chunks)} relevant chunks from ChromaDB for epoch {date_epoch}")
            return chunks

        except Exception as e:
            logger.error(f"Error searching ChromaDB: {e}")
            raise

    def _fetch_price_data(self, token: str, date: str, days_range: int = 7) -> List[Dict]:
        """
        Fetch price data from MongoDB for given token and date range

        Args:
            token: Token symbol (e.g., "BTC")
            date: Target date (YYYY-MM-DD format)
            days_range: Number of days before and after to fetch (default 7)

        Returns:
            List of price data documents
        """
        logger.info(f"Fetching price data for {token} around {date} (+/- {days_range} days)")

        try:
            # Parse target date
            target_date = datetime.strptime(date, "%Y-%m-%d")

            # Calculate date range
            start_date = (target_date - timedelta(days=days_range)).strftime("%Y-%m-%d")
            end_date = (target_date + timedelta(days=days_range)).strftime("%Y-%m-%d")

            # Connect to MongoDB
            mongodb_client = get_mongodb_client()
            local_db = mongodb_client.get_database("local")
            price_log_collection = local_db.get_collection("price.log")

            # Query price data
            query = {
                "coin_name": token.upper(),
                "date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }

            cursor = price_log_collection.find(query).sort("date", 1)
            price_data = list(cursor)

            # Convert ObjectId to string for JSON serialization
            for doc in price_data:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])

            logger.info(f"Found {len(price_data)} price records")
            return price_data

        except Exception as e:
            logger.error(f"Error fetching price data: {e}")
            raise

    def _count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """
        Count tokens in text using tiktoken

        Args:
            text: Text to count tokens for
            model: Model name to use for encoding (default: gpt-4o)

        Returns:
            Number of tokens in the text
        """
        try:
            encoding = tiktoken.encoding_for_model(model)
            tokens = encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Error counting tokens with tiktoken: {e}. Using estimate.")
            # Fallback: rough estimate (1 token ≈ 4 characters for English, less for other languages)
            return len(text) // 3

    def _generate_final_analysis(
        self,
        original_query: str,
        news_chunks: List[Dict],
        price_data: List[Dict]
    ) -> tuple[Dict, str, Dict]:
        """
        Generate final analysis using GPT-4o

        Args:
            original_query: Original user query
            news_chunks: Relevant news chunks from ChromaDB
            price_data: Price data from MongoDB

        Returns:
            Tuple of (Analysis result as JSON, Final user prompt string, Token usage info)
        """
        logger.info("Generating final analysis with GPT-4o...")

        # Prepare news chunks content (ALL chunks, not limited)
        chunks_content = "\n\n".join([
            f"[Article {i+1}]\n"
            f"Title: {chunk['metadata'].get('title', 'N/A')}\n"
            f"Date: {chunk['metadata'].get('publish_date', 'N/A')}\n"
            f"Content: {chunk['content']}"
            for i, chunk in enumerate(news_chunks)
        ])

        # Prepare price data content (ALL price records)
        price_content = self._format_price_data_full(price_data)

        # Build user prompt from template
        user_prompt = self.script_prompt_template.format(
            query=original_query,
            chunks=chunks_content,
            price_data=price_content
        )

        # Count tokens BEFORE sending to API
        system_prompt_tokens = self._count_tokens(self.analysis_prompt)
        user_prompt_tokens = self._count_tokens(user_prompt)
        total_input_tokens_estimated = system_prompt_tokens + user_prompt_tokens

        logger.info(f"📊 Token count (estimated via tiktoken):")
        logger.info(f"  - System prompt: {system_prompt_tokens:,} tokens")
        logger.info(f"  - User prompt: {user_prompt_tokens:,} tokens")
        logger.info(f"  - Total input: {total_input_tokens_estimated:,} tokens")

        try:
            system_message: ChatCompletionSystemMessageParam = {
                "role": "system",
                "content": self.analysis_prompt
            }
            user_message: ChatCompletionUserMessageParam = {
                "role": "user",
                "content": user_prompt
            }

            json_format: ResponseFormatJSONObject = {"type": "json_object"}

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[system_message, user_message],
                response_format=json_format,
                temperature=0.3
            )

            # Get actual token usage from API response
            actual_prompt_tokens = response.usage.prompt_tokens
            actual_completion_tokens = response.usage.completion_tokens
            actual_total_tokens = response.usage.total_tokens

            logger.info(f"📊 Token count (actual from API):")
            logger.info(f"  - Input tokens: {actual_prompt_tokens:,}")
            logger.info(f"  - Output tokens: {actual_completion_tokens:,}")
            logger.info(f"  - Total tokens: {actual_total_tokens:,}")

            # Calculate cost (gpt-4o pricing)
            input_cost = (actual_prompt_tokens / 1_000_000) * 2.50  # $2.50 per 1M input tokens
            output_cost = (actual_completion_tokens / 1_000_000) * 10.00  # $10.00 per 1M output tokens
            total_cost = input_cost + output_cost

            logger.info(f"💰 Estimated cost: ${total_cost:.4f}")

            token_usage = {
                "estimated": {
                    "system_prompt_tokens": system_prompt_tokens,
                    "user_prompt_tokens": user_prompt_tokens,
                    "total_input_tokens": total_input_tokens_estimated
                },
                "actual": {
                    "prompt_tokens": actual_prompt_tokens,
                    "completion_tokens": actual_completion_tokens,
                    "total_tokens": actual_total_tokens
                },
                "cost": {
                    "input_cost_usd": round(input_cost, 6),
                    "output_cost_usd": round(output_cost, 6),
                    "total_cost_usd": round(total_cost, 6)
                }
            }

            analysis = json.loads(response.choices[0].message.content)
            logger.info("Final analysis generated successfully")

            return analysis, user_prompt, token_usage

        except Exception as e:
            logger.error(f"Error generating final analysis: {e}")
            raise

    def _format_price_data_full(self, price_data: List[Dict]) -> str:
        """
        Format ALL price data into readable format (no limit)

        Args:
            price_data: List of price data documents

        Returns:
            Formatted price data string with all records
        """
        if not price_data:
            return "No price data available"

        formatted_lines = []
        for doc in price_data:
            date = doc.get("date", "Unknown")
            coin_name = doc.get("coin_name", "Unknown")
            price_info = doc.get("price_data", {})

            if price_info:
                time = price_info.get("time", "N/A")
                high = price_info.get("high", "N/A")
                low = price_info.get("low", "N/A")
                open_price = price_info.get("open", "N/A")
                close = price_info.get("close", "N/A")
                volumefrom = price_info.get("volumefrom", "N/A")
                volumeto = price_info.get("volumeto", "N/A")

                formatted_lines.append(
                    f"Coin: {coin_name} | Date: {date} | Time: {time} | "
                    f"Open: ${open_price} | High: ${high} | Low: ${low} | Close: ${close} | "
                    f"VolumeFrom: {volumefrom} | VolumeTo: ${volumeto}"
                )

        return "\n".join(formatted_lines)

    def _summarize_price_data(self, price_data: List[Dict]) -> str:
        """
        Summarize price data into readable format

        Args:
            price_data: List of price data documents

        Returns:
            Formatted price summary string
        """
        if not price_data:
            return "No price data available"

        summary_lines = []
        for doc in price_data:
            date = doc.get("date", "Unknown")
            price_info = doc.get("price_data", {})

            if price_info:
                high = price_info.get("high", "N/A")
                low = price_info.get("low", "N/A")
                close = price_info.get("close", "N/A")
                volume = price_info.get("volumeto", "N/A")

                summary_lines.append(
                    f"Date: {date} | High: ${high} | Low: ${low} | Close: ${close} | Volume: ${volume}"
                )

        return "\n".join(summary_lines[:20])  # Limit to 20 entries

    def make_script(self, query: str) -> Dict:
        """
        Main method to process user query and generate analysis

        Process:
        1. Parse query with GPT-4o to extract token and date
        2. Generate date range (7 days before and after)
        3. Search ChromaDB for each date (top_k=10 per date)
        4. Fetch price data from MongoDB
        5. Generate final analysis with GPT-4o

        Args:
            query: User's natural language query

        Returns:
            Complete analysis result with all data
        """
        logger.info(f"Starting RAG pipeline for query: {query}")

        try:
            # Step 1: Parse query
            parsed_data = self._parse_query_with_llm(query)
            token = parsed_data.get("token", "BTC")
            center_date_epoch = parsed_data.get("date_epoch", int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()))
            original_query = parsed_data.get("original_query", query)

            # Convert epoch to datetime for logging and price data
            center_datetime = datetime.fromtimestamp(center_date_epoch)
            center_date_str = center_datetime.strftime("%Y-%m-%d")

            # Step 2: Generate date range (7 days before and after) in epoch time
            epoch_range = []
            for days_offset in range(-7, 2):  # -7 to +7 (15 days total)
                target_datetime = center_datetime + timedelta(days=days_offset)
                # Set to start of day (00:00:00)
                target_epoch = int(target_datetime.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
                epoch_range.append(target_epoch)

            start_date_str = datetime.fromtimestamp(epoch_range[0]).strftime("%Y-%m-%d")
            end_date_str = datetime.fromtimestamp(epoch_range[-1]).strftime("%Y-%m-%d")
            logger.info(f"Searching news for date range: {start_date_str} to {end_date_str}")

            # Step 3: Search ChromaDB for each date (top_k=10 per date)
            all_news_chunks = []
            for date_epoch in epoch_range:
                chunks = self._search_chromadb(
                    query=original_query,
                    date_epoch=date_epoch,
                    top_k=2
                )
                all_news_chunks.extend(chunks)
                date_str = datetime.fromtimestamp(date_epoch).strftime("%Y-%m-%d")
                logger.info(f"Found {len(chunks)} chunks for date {date_str} (epoch: {date_epoch})")

            logger.info(f"Total news chunks collected: {len(all_news_chunks)}")

            # Step 4: Fetch price data
            price_data = self._fetch_price_data(
                token=token,
                date=center_date_str,
                days_range=7
            )

            # Step 5: Generate final analysis
            analysis, final_user_prompt, token_usage = self._generate_final_analysis(
                original_query=original_query,
                news_chunks=all_news_chunks,
                price_data=price_data
            )

            # Step 6: Compile complete result
            result = {
                "status": "success",
                "query": {
                    "original": query,
                    "parsed_token": token,
                    "parsed_date_epoch": center_date_epoch,
                    "parsed_date": center_date_str,
                    "date_range": {
                        "start": start_date_str,
                        "end": end_date_str,
                        "start_epoch": epoch_range[0],
                        "end_epoch": epoch_range[-1]
                    }
                },
                "data": {
                    "news_chunks_found": len(all_news_chunks),
                    "price_records_found": len(price_data),
                    "dates_searched": len(epoch_range)
                },
                "token_usage": token_usage,
                "prompts": {
                    "system_prompt": self.analysis_prompt,
                    "final_user_prompt": final_user_prompt
                },
                "analysis": analysis
            }

            logger.info("RAG pipeline completed successfully")
            return result

        except Exception as e:
            logger.error(f"Error in RAG pipeline: {e}")
            raise
