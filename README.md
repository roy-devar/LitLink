# LiteratureLink

## About
Literature Link is a personalized book recommendation system that uses algorithms like TF_IDF similarity, genre matching, and weighted scoring methods to find books to suggest users

## Setup
1. Clone the repo
 ```bash
 git clone https://github.com/roy-devar/LitLink.git
 ```
2. Change file paths in both python files to where ever your csv is located

3. Download the requirements.txt
```bash
 pip install -r requirements.txt
```
4. Start the Flask app
```bash
 python app.py
```
5. It should be running at the url
[http://127.0.0.1:5000](http://127.0.0.1:5000)

## Future Plans
- I have already implemented a favoriting system for users and i've implemented some of Collaborative Filtering algortihm but finishing it is my next goal.
- Expand to movie datasets or integrate GoodReads API

## Tech Stack
- Python, Flask, SQL, pandas, NumPy, scikit-learn, git