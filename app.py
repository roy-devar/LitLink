import pandas as pd
from data import combine_recs
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreateAcc, LoginAcc
from flask_sqlalchemy import SQLAlchemy
from rapidfuzz import process, fuzz
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

# Load book data and rename columns
bks_data = pd.read_csv("C:/Users/i3dch/Documents/project 1/goodreads_data.csv")
bks_data = bks_data.rename(columns={'Unnamed: 0': 'id'})

# Extract all book titles
book_titles = bks_data['Book'].dropna().tolist()

# Database models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    favorites = db.relationship('Favorite', back_populates='user')

class Book(db.Model):
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    favorites = db.relationship('Favorite', back_populates='book', cascade='all, delete-orphan')

class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    user = db.relationship('User', back_populates='favorites')
    book = db.relationship('Book', back_populates='favorites')

# Fuzzy search function
def search_book(query, book_titles, limit=5):
    results = process.extract(query, book_titles, limit=limit, scorer=fuzz.partial_ratio)
    return [book[0] for book in results if book[1] > 60]

# Fetch book cover using Google Books API
def fetch_book_cover(title):
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{title}"
        response = requests.get(url).json()
        return response['items'][0]['volumeInfo']['imageLinks']['thumbnail']
    except (KeyError, IndexError):
        return "https://via.placeholder.com/128x196?text=No+Cover"

# Initialize database with books
with app.app_context():
    existing_books = set(b.id for b in Book.query.all())
    for _, row in bks_data.iterrows():
        if row['id'] not in existing_books:
            new_book = Book(id=row['id'], title=row['Book'])
            db.session.add(new_book)
    db.session.commit()

# Home page route
@app.route('/', methods=['GET', 'POST'])
def index():
    recommendations = []
    searched_book = None
    user_favs = []
    user = None

    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user_favs = [
                {
                    "title": favorite.book.title,
                    "cover": fetch_book_cover(favorite.book.title),
                    "id": favorite.book.id
                }
                for favorite in user.favorites if favorite.book
            ]

    if request.method == 'POST':
        title = request.form['title']
        matched_titles = search_book(title, book_titles)
        if matched_titles:
            searched_title = matched_titles[0]
            searched_book_row = bks_data[bks_data['Book'] == searched_title].iloc[0]
            searched_book = {
                "id": searched_book_row['id'],
                "title": searched_book_row['Book'],
                "cover": fetch_book_cover(searched_book_row['Book'])
            }
            recommendations = combine_recs(searched_title, bks_data)
            recommendations = [
                {
                    "id": rec["id"],
                    "title": rec["Book"],
                    "cover": fetch_book_cover(rec["Book"])
                }
                for rec in recommendations
            ]

    return render_template('index.html', searched_book=searched_book, recommendations=recommendations, favorites=user_favs, user=user)


# Registration route
@app.route('/register', methods=['GET', 'POST'])
def create_account():
    form = CreateAcc()
    if form.validate_on_submit():
        username = form.username.data
        password = generate_password_hash(form.password.data)
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginAcc()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password'
    return render_template('login.html', form=form)

# Route to favorite a book
@app.route('/favorite/<int:book_id>', methods=['POST'])
def favorite_book(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    book = Book.query.get(book_id)
    if book is None:
        return "Book not found", 404

    existing_fav = Favorite.query.filter_by(user_id=user_id, book_id=book_id).first()
    if not existing_fav:
        new_fav = Favorite(user_id=user_id, book_id=book_id)
        db.session.add(new_fav)
        db.session.commit()

    return redirect(url_for('index'))

# Route to remove a book from favorites
@app.route('/remove_favorite/<int:book_id>', methods=['POST'])
def remove_favorite(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    favorite = Favorite.query.filter_by(user_id=user_id, book_id=book_id).first()
    if favorite:
        db.session.delete(favorite)
        db.session.commit()

    return redirect(url_for('index'))

# Search route
@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    matched_books = search_book(query, book_titles) if query else []
    return render_template('index.html', books=matched_books, recommendations=[], favorites=[], user=None)

# Route to generate recommendations for a specific book
@app.route('/recommend/<book_title>')
def recommend_book(book_title):
    if book_title not in bks_data['Book'].values:
        return "Book not found", 404

    recommendations = combine_recs(book_title, bks_data)
    for rec in recommendations:
        if 'Book' in rec:
            rec['cover'] = fetch_book_cover(rec['Book'])
        else:
            rec['cover'] = "https://via.placeholder.com/128x196?text=No+Cover"

    searched_book = bks_data[bks_data['Book'] == book_title].iloc[0]
    searched_book_data = {
        'title': searched_book['Book'],
        'id': searched_book['id'],
        'cover': fetch_book_cover(searched_book['Book'])
    }

    return render_template(
        'recommendations.html',
        searched_book=searched_book_data,
        recommendations=recommendations
    )

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
