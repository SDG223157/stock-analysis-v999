from flask import Blueprint, render_template, request, make_response, jsonify
from datetime import datetime
import yfinance as yf
import logging
import sys
import traceback
from app.utils.analysis import create_combined_analysis
from app.utils.tickers import TICKERS, TICKER_DICT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create Blueprint
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('index.html', now=datetime.now(), max_date=today)

@bp.route('/search_ticker', methods=['GET'])
def search_ticker():
    query = request.args.get('query', '').upper()
    if not query or len(query) < 1:
        return jsonify([])
    
    try:
        search_results = []
        logger.info(f"Searching for ticker: {query}")
        
        # Exact match
        if query in TICKER_DICT:
            search_results.append({
                'symbol': query,
                'name': TICKER_DICT[query],
                'source': 'predefined'
            })
            logger.info(f"Found exact match: {query}")
        
        # Partial matches
        if len(search_results) < 5:
            partial_matches = [
                {'symbol': ticker['symbol'], 'name': ticker['name'], 'source': 'predefined'}
                for ticker in TICKERS
                if (query in ticker['symbol'].upper() or 
                    query in ticker['name'].upper()) and 
                    ticker['symbol'] != query
            ]
            search_results.extend(partial_matches[:5 - len(search_results)])
            logger.info(f"Found {len(partial_matches)} partial matches")
        
        # Sort results
        search_results.sort(key=lambda x: (
            x['symbol'] != query,  # Exact matches first
            len(x['symbol']),     # Shorter symbols next
            x['symbol']           # Alphabetical order
        ))
        
        return jsonify(search_results[:5])
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify([])

@bp.route('/analyze', methods=['POST'])
def analyze():
    try:
        ticker_input = request.form.get('ticker', '').split()[0].upper()
        logger.info(f"Analyzing ticker: {ticker_input}")
        
        if not ticker_input:
            raise ValueError("Ticker symbol is required")
        
        # Handle region-specific ticker formats
        if ticker_input in TICKER_DICT:
            ticker = ticker_input
            logger.info(f"Using predefined ticker: {ticker}")
        else:
            matching_tickers = [t['symbol'] for t in TICKERS if t['symbol'].startswith(ticker_input)]
            ticker = matching_tickers[0] if matching_tickers else ticker_input
            logger.info(f"Using matched ticker: {ticker}")
        
        # Handle end date
        end_date = request.form.get('end_date')
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
                logger.info(f"Using end date: {end_date}")
            except ValueError:
                raise ValueError("Invalid date format. Please use YYYY-MM-DD format")
        else:
            end_date = None
            logger.info("Using current date")
        
        try:
            lookback_days = int(request.form.get('lookback_days', 365))
            if lookback_days < 30 or lookback_days > 1825:
                raise ValueError("Lookback days must be between 30 and 1825")
            logger.info(f"Using lookback days: {lookback_days}")
        except ValueError:
            raise ValueError("Invalid lookback days value")
            
        try:
            crossover_days = int(request.form.get('crossover_days', 180))
            if crossover_days < 30 or crossover_days > 365:
                raise ValueError("Crossover days must be between 30 and 365")
            logger.info(f"Using crossover days: {crossover_days}")
        except ValueError:
            raise ValueError("Invalid crossover days value")
        
        # Perform analysis
        try:
            logger.info("Starting technical analysis...")
            _, fig, _, _ = create_combined_analysis(
                ticker,
                end_date=end_date,
                lookback_days=lookback_days,
                crossover_days=crossover_days
            )
            logger.info("Analysis completed successfully")
            
            html_content = fig.to_html(
                full_html=True,
                include_plotlyjs=True,
                config={'responsive': True}
            )
            
            response = make_response(html_content)
            response.headers['Content-Type'] = 'text/html'
            return response
            
        except Exception as analysis_error:
            logger.error(f"Analysis failed: {str(analysis_error)}")
            raise ValueError(f"Analysis failed: {str(analysis_error)}")
        
    except Exception as e:
        error_msg = f"Error analyzing {ticker_input}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        error_html = f"""
        <html>
            <head>
                <title>Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 2rem; }}
                    .error {{ color: #dc3545; padding: 1rem; background-color: #f8d7da; 
                             border: 1px solid #f5c6cb; border-radius: 3px; }}
                    .back-link {{ margin-top: 1rem; display: block; }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h2>Analysis Error</h2>
                    <p>{error_msg}</p>
                </div>
                <a href="javascript:window.close();" class="back-link">Close Window</a>
            </body>
        </html>
        """
        return error_html, 500
