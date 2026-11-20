# Space Search

A mini search engine for space topics, built in Python with Streamlit.
It indexes Wikipedia articles, ranks them with TF-IDF, and shows an
overview made from the best sentences at the top of the results.

## Files

- `app.py`: the Streamlit web page
- `indexer.py`: tokeniser, inverted index, ranking and overview
- `wiki.py`: functions for talking to Wikipedia's API
- `crawler.py`: bulk crawler that builds the starting library of articles
- `data/pages/`: the saved articles (plain text)

## Run it

Mac:

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    streamlit run app.py

Windows:

    py -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py

The app opens at http://localhost:8501.

## Data

Article text comes from Wikipedia.