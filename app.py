# Imports and initial setup
import pandas as pd
from data import combine_recs
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreateAcc, LoginAcc
from flask_sqlalchemy import SQLAlchemy
from rapidfuzz import process, fuzz

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

# Load book data and renaming Unnamed: 0 column to id
bks_data = pd.read_csv("C:/Users/i3dch/Documents/project 1/goodreads_data.csv")
bks_data = bks_data.rename(columns={'Unnamed: 0': 'id'})

# Extract all book titles from the dataset
book_titles = bks_data['Book'].dropna().tolist()

# Database models for user and favorite books
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

# Book search function
def search_book(query, book_titles, limit=5):
    results = process.extract(query, book_titles, limit=limit, scorer=fuzz.partial_ratio)
    return [book[0] for book in results if book[1] > 60]


with app.app_context():
    # Check if books already exist in the database
    existing_books = set(b.id for b in Book.query.all())
    
    for _, row in bks_data.iterrows():
        if row['id'] not in existing_books:
            new_book = Book(id=row['id'], title=row['Book'])
            db.session.add(new_book)
    
    db.session.commit()

# Home page route main recommendation function
@app.route('/', methods=['GET', 'POST'])
def index():
    recommendations = []
    user_favs = []
    user = None

    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user_favs = [favorite.book for favorite in user.favorites if favorite.book]

    if request.method == 'POST':
        title = request.form['title']
        recommendations = combine_recs(title, bks_data)

    return render_template('index.html', recommendations=recommendations, favorites=user_favs, user=user)

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
    searched_book = bks_data[bks_data['Book'] == book_title].iloc[0]
    searched_book_data = {
        'title': searched_book['Book'],
        'id': searched_book['id'],
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
