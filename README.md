# Quantpedia Strategy Screener

## Overview
The Quantpedia Strategy Screener is a sophisticated web application that provides an interactive interface for browsing, filtering, and analyzing investment strategies from Quantpedia. It features AI-powered summarization using Groq's llama-3.3-70b-specdec and qwen-qwq-32b models, efficient caching mechanisms, and comprehensive filtering options.

## Features
- Web-based interface for exploring investment strategies
- AI-powered strategy summarization using multiple models
- Advanced filtering and sorting capabilities
- Keyword-based strategy categorization
- Caching system for improved performance
- Comprehensive strategy metadata analysis

## Technical Stack
- **Backend**: Flask (Python)
- **Frontend**: HTML/CSS/JavaScript
- **AI Models**: 
  - Groq llama-3.3-70b-specdec
  - Groq qwen-qwq-32b
- **Data Processing**: 
  - BeautifulSoup4 for HTML parsing
  - Pandas for data manipulation
  - Markdown for text formatting

## Directory Structure
```
.
├── app.py                         # Main Flask application
├── requirements.txt               # Python dependencies
├── templates/                     # HTML templates
├── html_files/                   # Strategy HTML content
├── metadata_files/               # Strategy metadata JSON files
├── icons/                        # Application icons
├── logs/                         # Application logs
├── InvestmentStrategies.app/     # macOS application bundle
├── create_app_with_icon.sh       # Script to create macOS app
├── launch_investment_app.command  # App launch script
└── .env                          # Environment configuration
```

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Set up environment variables in `.env` file (see Configuration section)
4. Run the application:
```bash
python app.py
```

## Configuration
The application requires several API keys and configuration settings in the `.env` file:
- GROQ_API_KEY: For Groq LLM model access
- Additional optional API keys for extended functionality

## macOS Application
The repository includes scripts to create a standalone macOS application:
- `create_app_with_icon.sh`: Creates the application bundle
- `launch_investment_app.command`: Launches the application
- Custom application icon included

## Data Structure
- Strategy metadata stored in JSON format
- HTML content for each strategy
- Cached data for improved performance
- Keyword-based categorization system

## Features in Detail

### Strategy Analysis
- Comprehensive strategy metadata
- Historical performance data
- Backtest period information
- Sharpe ratio calculations
- Keyword categorization

### AI Summarization
- Dual-model approach using Claude and DeepSeek
- Cached summaries for performance
- Natural language processing of strategy descriptions

### Filtering and Sorting
- Multiple sorting options
- Keyword-based filtering
- Performance metrics filtering
- Date range selection

## Development

### Prerequisites
- Python 3.8+
- macOS for application bundle creation
- Required API keys for AI models

### Local Development
1. Set up a Python virtual environment
2. Install development dependencies
3. Run Flask in development mode

### Building the macOS App
```bash
./create_app_with_icon.sh
```

## Performance Considerations
- LRU caching for frequently accessed data
- Optimized database queries
- Parallel processing for AI summarization
- Memory-efficient data handling

## Error Handling
- Comprehensive logging system
- Graceful fallback for missing data
- API error handling
- Cache invalidation management

## Security
- Environment variable-based configuration
- API key protection
- Input validation
- Secure data handling

## Contributing
Contributions are welcome! Please follow these steps:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License
[Insert License Information]

## Contact
[Insert Contact Information]

## Version History
- Current Version: 1.0.0
- Last Updated: [Current Date] 