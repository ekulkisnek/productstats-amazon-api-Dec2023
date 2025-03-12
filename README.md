
# Keepa API Product Analyzer

A web-based tool that processes product data through the Keepa API to analyze Amazon product rankings, prices, and sales metrics. This application helps sellers make data-driven decisions by providing insights into product performance metrics.

## Features

- **CSV Upload**: Upload product data in CSV format for analysis
- **Keepa API Integration**: Fetch detailed product metrics through Keepa's API
- **Dashboard View**: Simple interface showing processing status and navigation
- **Settings Configuration**: Customize ranking thresholds and notification preferences
- **Results Filtering**: View all results, recent hits, or all hits with sorting options
- **History Tracking**: Access previously processed files

## Requirements

- Python 3.10+
- Flask web framework
- Keepa API key (set as environment variable)
- Pandas for data processing

## Installation

1. Clone the repository
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Set up your Keepa API key as an environment variable:
```
export KEEPA_API_KEY=your_keepa_api_key_here
```

## Usage

1. Run the application:
```
python main.py
```
2. Open your browser and navigate to `http://localhost:8080`
3. Use the passcode `1234` to log in (if PASSCODE_ENABLED is set to True)
4. Upload a CSV file containing product IDs in the format required by Keepa
5. View the results and apply filters as needed

## Input File Format

The input CSV should contain at minimum a column labeled `productId` with Amazon product IDs (ASIN). Additional columns may be included and will be preserved in the results.

## Configuration

- `SETTINGS_FILE`: Path to settings JSON file (default: `settings.json`)
- `UPLOAD_FOLDER`: Directory for uploaded files (default: `uploads`)
- `ALLOWED_EXTENSIONS`: File types allowed for upload (default: CSV only)
- `PASSCODE_ENABLED`: Enable/disable login security (default: False)

## Settings

The following settings can be configured in the web interface:

- **Rank**: Minimum sales rank threshold
- **Monthly Sales**: Minimum monthly sales threshold
- **Sales Price**: Minimum price threshold
- **Notification Settings**: Email and text contact information for alerts

## API Processing

The application processes product data through the Keepa API with the following steps:

1. Reading uploaded CSV files
2. Extracting product IDs
3. Querying the Keepa API for each product
4. Extracting relevant data (rank, price, sales)
5. Saving results to a CSV file

## Error Handling

- File type validation
- API connection error recovery with retry logic
- Token management to prevent API rate limiting

## Limitations

- Processing speed depends on Keepa API rate limits
- Large files may take significant time to process

## Security

- Basic passcode protection available
- Environment variable used for API key storage
- Uploaded files are stored in a dedicated folder

## License

[Your License Information]

## Contributors

[Your Name/Organization]
