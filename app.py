"""
Quantpedia Strategy Screener

This Flask application provides a web interface for browsing, filtering, and analyzing
investment strategies from Quantpedia. It features AI-powered summarization using
Groq's LLM models (openai/gpt-oss-120b and moonshotai/kimi-k2-instruct), caching mechanisms for improved performance,
and comprehensive filtering options.

The application loads strategy metadata from JSON files, enhances it with additional
information extracted from HTML files, and provides API endpoints for the frontend
to interact with this data.

Author: [Your Name]
Version: 1.0.0
Date: [Current Date]
"""

from flask import Flask, render_template, request, jsonify
import json
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import markdown
from pathlib import Path
import groq
from concurrent.futures import ThreadPoolExecutor
import re
from functools import lru_cache
import requests
from urllib.parse import quote

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client
groq_api_key = os.getenv('GROQ_API_KEY')
groq_client = None
MODEL_CONFIG = {
    "primary": {"id": "openai/gpt-oss-120b", "label": "GPT-OSS 120B"},
    "secondary": {"id": "moonshotai/kimi-k2-instruct", "label": "Kimi K2 Instruct (1T)"}
}

# Log API key status
if not groq_api_key:
    print("Warning: GROQ_API_KEY not found in environment variables. Summaries will not work.")
else:
    print("Groq API key found")
    groq_client = groq.Groq(api_key=groq_api_key)

# Load model configuration from root file 'models' if present
def load_models_config():
    global MODEL_CONFIG
    try:
        cfg_path = Path("models")
        if cfg_path.exists():
            with open(cfg_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Validate minimal structure
                if "primary" in data and "id" in data["primary"] and "label" in data["primary"] \
                   and "secondary" in data and "id" in data["secondary"] and "label" in data["secondary"]:
                    MODEL_CONFIG = data
                    print(f"Loaded model config: primary={MODEL_CONFIG['primary']['id']}, secondary={MODEL_CONFIG['secondary']['id']}")
                else:
                    print("Model config missing required fields; using defaults")
        else:
            print("Model config file 'models' not found; using defaults")
    except Exception as e:
        print(f"Error loading model config: {e}. Using defaults")

# Load on startup
load_models_config()

# Initialize Flask application
app = Flask(__name__)

# Cache for strategies to improve performance
# _strategy_cache: Stores the loaded strategies
# _last_load_time: Timestamp of the last cache update
_strategy_cache = None
_last_load_time = 0

@lru_cache(maxsize=1000)
def get_html_filename(strategy_title):
    """Get the correct HTML filename for a strategy, handling special characters"""
    try:
        # Try different filename variations
        variations = [
            strategy_title.replace(' ', '_'),  # Simple replacement
            quote(strategy_title.replace(' ', '_')),  # URL encoded
            strategy_title.replace(' ', '_').replace('?', '%3F').replace(':', '%3A').replace('&', '%26').replace(',', '%2C')  # Manual encoding of common special chars
        ]
        
        for filename in variations:
            html_file = f"html_files/{filename}.html"
            if os.path.exists(html_file):
                return html_file
                
        print(f"HTML file not found for strategy: {strategy_title}")
        return None
    except Exception as e:
        print(f"Error getting HTML filename for strategy {strategy_title}: {str(e)}")
        return None

@lru_cache(maxsize=1000)
def get_date(strategy_title):
    """Cached function to get the end date for a strategy"""
    try:
        html_file = get_html_filename(strategy_title)
        if not html_file:
            return 0
            
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        pattern = r'Backtest period from source paper</div><div[^>]*>(\d{4})-(\d{4})</div>'
        match = re.search(pattern, html_content)
        
        if match:
            end_year = int(match.group(2))
            return end_year
        else:
            print(f"No backtest period found for strategy: {strategy_title}")
            return 0
    except Exception as e:
        print(f"Error getting date for strategy {strategy_title}: {str(e)}")
        return 0

@lru_cache(maxsize=1000)
def get_keywords(strategy_title):
    """Cached function to get keywords for a strategy"""
    try:
        html_file = get_html_filename(strategy_title)
        if not html_file:
            return []
            
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        soup = BeautifulSoup(html_content, 'html.parser')
        keywords_div = soup.find('div', class_='large-12 mrg-top-40 mrg-btm-50')
        
        if keywords_div:
            keywords = []
            for keyword_link in keywords_div.find_all('a', class_='keyword'):
                href = keyword_link.get('href', '')
                if 'strategy-tags/' in href:
                    keyword = href.split('strategy-tags/')[-1].rstrip('/')
                    # Normalize keyword by replacing hyphens with spaces and converting to lowercase
                    keyword = keyword.replace('-', ' ').lower()
                    keywords.append(keyword)
            return keywords
        else:
            print(f"No keywords div found for strategy: {strategy_title}")
            return []
    except Exception as e:
        print(f"Error getting keywords for strategy {strategy_title}: {str(e)}")
        return []

def load_strategies(force_reload=False):
    """Load all strategy metadata from JSON files with caching"""
    global _strategy_cache, _last_load_time
    current_time = os.path.getmtime("metadata_files") if os.path.exists("metadata_files") else 0
    
    # Return cached data if available and not forced to reload
    if not force_reload and _strategy_cache is not None and current_time <= _last_load_time:
        return _strategy_cache
        
    strategies = []
    metadata_dir = Path("metadata_files")
    
    if not metadata_dir.exists():
        print(f"Warning: Directory {metadata_dir} does not exist")
        return []
        
    for file in metadata_dir.glob("*.json"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                strategy = json.load(f)
                strategy['filename'] = file.name
                strategy['end_year'] = get_date(strategy.get('title', ''))
                strategy['keywords'] = get_keywords(strategy.get('title', ''))
                strategies.append(strategy)
        except Exception as e:
            print(f"Error loading {file}: {e}")
            continue
    
    # Update cache
    _strategy_cache = strategies
    _last_load_time = current_time
    return strategies

def get_html_content(strategy_name):
    """Get HTML content for a strategy"""
    try:
        # Clean up the filename - remove .json extension if present
        if strategy_name.endswith('.json'):
            strategy_name = strategy_name[:-5]
            
        # Replace spaces with underscores and ensure it's a valid filename
        strategy_name = strategy_name.replace(' ', '_')
        
        html_path = Path("html_files") / f"{strategy_name}.html"
        print(f"Looking for HTML file at: {html_path.absolute()}")
        
        if not html_path.parent.exists():
            print(f"HTML directory does not exist: {html_path.parent.absolute()}")
            return None
            
        if not html_path.exists():
            print(f"HTML file not found: {html_path.absolute()}")
            return None
            
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                print(f"HTML file is empty: {html_path.absolute()}")
                return None
            print(f"Successfully loaded HTML content from: {html_path.absolute()}")
            return content
    except Exception as e:
        print(f"Error loading HTML for {strategy_name}: {str(e)}")
        import traceback
        print("Traceback:", traceback.format_exc())
        return None

def summarize_strategy_kimi(text):
    """Use Groq's moonshotai/kimi-k2-instruct (Kimi K2 Instruct 1T) to summarize strategy content"""
    try:
        if not groq_api_key:
            raise ValueError("Groq API key is not set")
            
        response = groq_client.chat.completions.create(
            model=MODEL_CONFIG.get("secondary", {}).get("id", "moonshotai/kimi-k2-instruct"),
            messages=[
                {"role": "system", "content": "You are an expert in finance and investment strategies. Provide a thorough analysis of investment strategies."},
                {"role": "user", "content": "Summarize this investment strategy in one paragraph:\n\n" + text[:50000]}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        import traceback
        return f"Error generating kimi summary: {str(e)}"

def summarize_strategy_gptoss(text):
    """Use Groq's openai/gpt-oss-120b model to summarize strategy content"""
    try:
        if not groq_api_key:
            raise ValueError("Groq API key is not set")
            
        response = groq_client.chat.completions.create(
            model=MODEL_CONFIG.get("primary", {}).get("id", "openai/gpt-oss-120b"),
            stream=False,  # Explicitly disable streaming
            messages=[
                {"role": "system", "content": "You are an expert in finance and investment strategies. Provide a thorough analysis of investment strategies."},
                {"role": "user", "content": "Summarize this investment strategy in one paragraph:\n\n" + text[:50000]}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        import traceback
        return f"Error generating gpt-oss summary: {str(e)}"
    
def summarize_strategy(html_content):
    """Use both Groq models to summarize strategy content"""
    try:
        # Reload model config at runtime so updates to 'models' file take effect without restart
        load_models_config()
        if not html_content:
            return {"error": "No content to summarize"}
            
        # Extract text from HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        if not text.strip():
            return {"error": "No text content found in HTML"}
        
        # Create a thread pool executor for parallel API calls
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both API calls
            gptoss_future = executor.submit(summarize_strategy_gptoss, text)
            kimi_future = executor.submit(summarize_strategy_kimi, text)
            
            # Get results
            gptoss_summary = gptoss_future.result()
            kimi_summary = kimi_future.result()
            
        return {
            # Keep the keys the same for frontend compatibility, but map to new models:
            # openai_summary -> GPT-OSS 120B; anthropic_summary -> Kimi K2 Instruct
            "openai_summary": gptoss_summary,
            "anthropic_summary": kimi_summary
        }
        
    except Exception as e:
        return {"error": f"Error generating summaries: {str(e)}"}

def sort_strategies(strategies, sort_field):
    print(f"\nSorting by {sort_field}...")
    
    def get_sharpe(strategy):
        return float(strategy.get('performance_metrics', {}).get('sharpe_ratio', 0) or 0)
    
    if sort_field == "sharpe":
        return sorted(strategies, key=get_sharpe, reverse=True)
    elif sort_field == "title":
        return sorted(strategies, key=lambda x: x.get('title', '').lower())
    elif sort_field == "date":
        # Create a composite key that combines date and sharpe ratio
        def sort_key(strategy):
            date = get_date(strategy.get('title', ''))
            sharpe = get_sharpe(strategy)
            # Return a tuple that will sort by date descending, then sharpe descending
            return (-date, -sharpe)
            
        return sorted(strategies, key=sort_key)
    
    return strategies

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Error loading template: {str(e)}", 500

@app.route('/api/strategies')
def get_strategies_endpoint():
    try:
        # Get query parameters
        min_sharpe = request.args.get('min_sharpe', type=float)
        max_drawdown = request.args.get('max_drawdown', type=float)
        trading_frequency = request.args.get('trading_frequency')
        search_query = request.args.get('search', '').lower()
        sort_by = request.args.get('sort_by', 'sharpe')
        asset_classes = request.args.getlist('asset_classes[]')
        keywords = [k.replace('-', ' ').lower() for k in request.args.getlist('keywords[]')]

        print(f"\nSelected keywords: {keywords}")
        print(f"Selected asset classes: {asset_classes}")

        # Load strategies
        strategies = load_strategies()
        
        # Filter strategies
        filtered_strategies = []
        for strategy in strategies:
            # Start with basic filters
            should_include = True
            
            # Check performance metrics if provided
            if min_sharpe and float(strategy.get('performance_metrics', {}).get('sharpe_ratio', 0) or 0) < min_sharpe:
                continue
                
            if max_drawdown and abs(float(strategy.get('performance_metrics', {}).get('max_drawdown', 0) or 0)) > abs(float(max_drawdown)):
                continue
                
            # Check trading frequency if provided
            if trading_frequency and strategy.get('implementation', {}).get('trading_frequency') != trading_frequency:
                continue

            # Check asset classes if provided - using OR logic (ANY asset matches)
            if asset_classes:
                strategy_assets = [asset.lower() for asset in strategy.get('asset_classes', [])]
                
                # If no asset class matches, exclude this strategy
                if not any(asset_class.lower() in strategy_assets for asset_class in asset_classes):
                    continue
            
            # Check keywords if provided - using OR logic (ANY keyword matches)
            if keywords:
                # Clean up strategy keywords
                strategy_keywords = [k.replace('-', ' ').lower().strip() for k in strategy.get('keywords', [])]
                title = strategy.get('title', '').lower()
                
                # Debug information
                print(f"Checking strategy: {title}")
                print(f"Strategy keywords: {strategy_keywords}")
                
                # Use a more flexible matching approach
                matched = False
                matching_keywords = []
                
                for user_keyword in keywords:
                    for strategy_keyword in strategy_keywords:
                        # Check if keyword appears as a substring
                        if user_keyword in strategy_keyword or strategy_keyword in user_keyword:
                            print(f"✅ Match found: User '{user_keyword}' ~ Strategy '{strategy_keyword}'")
                            matched = True
                            matching_keywords.append(user_keyword)
                            break
                
                if not matched:
                    print(f"❌ No keyword matches for {title}")
                    continue
                else:
                    print(f"✅ Strategy matched keywords: {matching_keywords}")
                
            # Check search query
            if search_query:
                title = strategy.get('title', '').lower()
                description = strategy.get('description', '').lower()
                if search_query not in title and search_query not in description:
                    continue
                    
            # If we got here, all filters passed
            filtered_strategies.append(strategy)
            
        # Sort strategies
        sorted_strategies = sort_strategies(filtered_strategies, sort_by)
        
        print(f"Total filtered strategies: {len(filtered_strategies)}")
        return jsonify(sorted_strategies)
        
    except Exception as e:
        print(f"Error in get_strategies_endpoint: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/strategy/<strategy_name>/summary')
def get_strategy_summary(strategy_name):
    try:
        print(f"Fetching summary for strategy: {strategy_name}")
        html_content = get_html_content(strategy_name)
        
        if not html_content:
            error_msg = f"No HTML content found for strategy: {strategy_name}"
            print(error_msg)
            return jsonify({"error": error_msg}), 404
            
        print("HTML content found, generating summaries...")
        summaries = summarize_strategy(html_content)
        
        if "error" in summaries:
            print(f"Error in summarization: {summaries['error']}")
            return jsonify(summaries), 500
            
        print("Successfully generated summaries")
        return jsonify(summaries)
            
    except Exception as e:
        error_msg = f"Error processing strategy summary: {str(e)}"
        print(f"Exception in get_strategy_summary: {error_msg}")
        import traceback
        print("Traceback:", traceback.format_exc())
        return jsonify({"error": error_msg}), 500

@app.route('/api/strategy/<strategy_name>/content')
def get_strategy_content(strategy_name):
    try:
        html_content = get_html_content(strategy_name)
        
        if html_content:
            return html_content
            
        return "Strategy content not found", 404
    except Exception as e:
        return f"Error loading strategy content: {str(e)}", 500

@app.route('/strategy/<strategy_name>/view')
def view_strategy(strategy_name):
    """Display a strategy in a formatted view with navigation and styling"""
    try:
        # Get the HTML content
        html_content = get_html_content(strategy_name)
        
        if not html_content:
            return "Strategy content not found", 404
            
        # Get strategy metadata if available
        strategies = load_strategies()
        strategy_info = None
        
        for strategy in strategies:
            if strategy.get('filename', '').replace('.json', '') == strategy_name:
                strategy_info = strategy
                break
        
        # Render the strategy view template with the content and metadata
        return render_template(
            'strategy_view.html',
            content=html_content,
            strategy=strategy_info,
            title=strategy_info.get('title', strategy_name) if strategy_info else strategy_name
        )
    except Exception as e:
        print(f"Error in view_strategy: {str(e)}")
        import traceback
        print("Traceback:", traceback.format_exc())
        return f"Error displaying strategy: {str(e)}", 500

@app.route('/api/keywords')
def get_keywords_summary():
    """Get a summary of all keywords and their counts"""
    strategies = load_strategies()
    
    # Collect all keywords and their counts
    keyword_counts = {}
    keyword_strategies = {}
    
    for strategy in strategies:
        keywords = strategy.get('keywords', [])
        for keyword in keywords:
            if keyword in keyword_counts:
                keyword_counts[keyword] += 1
                keyword_strategies[keyword].append(strategy['title'])
            else:
                keyword_counts[keyword] = 1
                keyword_strategies[keyword] = [strategy['title']]
    
    # Categorize keywords
    categories = {
        'Trading Style': ['momentum', 'reversal', 'trend following', 'mean reversion', 'arbitrage', 'carry', 'volatility', 'pairs trading'],
        'Asset Class': ['stocks', 'bonds', 'forex', 'commodities', 'options', 'futures', 'crypto', 'etf'],
        'Factor Type': ['value', 'size', 'quality', 'low volatility', 'growth', 'profitability', 'liquidity'],
        'Time Horizon': ['intraday', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'],
        'Market': ['equity', 'fixed income', 'currency', 'commodity', 'cryptocurrency'],
        'Region': ['global', 'us', 'europe', 'asia', 'emerging markets', 'china', 'japan'],
        'Other': []
    }
    
    # Categorize each keyword
    categorized_keywords = {cat: {} for cat in categories}
    
    for keyword, count in keyword_counts.items():
        keyword_lower = keyword.lower().replace('-', ' ')
        categorized = False
        
        for category, keywords in categories.items():
            if any(k in keyword_lower for k in keywords):
                categorized_keywords[category][keyword] = {
                    'count': count,
                    'strategies': keyword_strategies[keyword]
                }
                categorized = True
                break
        
        if not categorized:
            categorized_keywords['Other'][keyword] = {
                'count': count,
                'strategies': keyword_strategies[keyword]
            }
    
    return jsonify(categorized_keywords)

@app.route('/api/models')
def get_models():
    """Return the configured model IDs and labels used for summarization"""
    try:
        # Reload on each call to allow runtime updates without restart
        load_models_config()
        return jsonify({
            "primary": MODEL_CONFIG.get("primary", {}),
            "secondary": MODEL_CONFIG.get("secondary", {})
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/keywords/summary')
def get_keywords_summary_counts():
    """Get a summary of all keywords and their counts without strategy details"""
    strategies = load_strategies()
    
    # Collect all keywords and their counts
    keyword_counts = {}
    
    for strategy in strategies:
        keywords = strategy.get('keywords', [])
        for keyword in keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
    
    # Categorize keywords
    categories = {
        'Trading Style': ['momentum', 'reversal', 'trend following', 'mean reversion', 'arbitrage', 'carry', 'volatility', 'pairs trading'],
        'Asset Class': ['stocks', 'bonds', 'forex', 'commodities', 'options', 'futures', 'crypto', 'etf'],
        'Factor Type': ['value', 'size', 'quality', 'low volatility', 'growth', 'profitability', 'liquidity'],
        'Time Horizon': ['intraday', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'],
        'Market': ['equity', 'fixed income', 'currency', 'commodity', 'cryptocurrency'],
        'Region': ['global', 'us', 'europe', 'asia', 'emerging markets', 'china', 'japan'],
        'Other': []
    }
    
    # Categorize each keyword
    categorized_keywords = {cat: [] for cat in categories}
    
    for keyword, count in sorted(keyword_counts.items(), key=lambda x: (-x[1], x[0])):
        keyword_lower = keyword.lower().replace('-', ' ')
        categorized = False
        
        for category, keywords in categories.items():
            if any(k in keyword_lower for k in keywords):
                categorized_keywords[category].append({
                    'keyword': keyword,
                    'count': count
                })
                categorized = True
                break
        
        if not categorized:
            categorized_keywords['Other'].append({
                'keyword': keyword,
                'count': count
            })
    
    return jsonify(categorized_keywords)

if __name__ == '__main__':
    import socket
    from contextlib import closing

    # Make sure required directories exist
    templates_dir = Path("templates")
    if not templates_dir.exists():
        templates_dir.mkdir()
        
    metadata_dir = Path("metadata_files")
    if not metadata_dir.exists():
        metadata_dir.mkdir()
        
    html_dir = Path("html_files")
    if not html_dir.exists():
        html_dir.mkdir()

    # Use PORT environment variable for deployment (Heroku, etc.)
    port = int(os.environ.get('PORT', 8092))
    url = f'http://127.0.0.1:{port}'
    
    print(f"\nStarting server at {url}")
    print("Press Ctrl+C to quit\n")
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)