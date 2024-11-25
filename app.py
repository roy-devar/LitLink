# Imports and initial setup
import pandas as pd
from data import combine_recs
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreateAcc, LoginAcc
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

# Load book data, renaming `Unnamed: 0` column to `id`
bks_data = pd.read_csv("C:/Users/i3dch/Documents/project 1/goodreads_data.csv")
bks_data = bks_data.rename(columns={'Unnamed: 0': 'id'})

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

# Initialize database with app context
# Insert books from the CSV into the database
with app.app_context():
    # Check if books already exist in the database
    existing_books = set(b.id for b in Book.query.all())
    
    for _, row in bks_data.iterrows():
        if row['id'] not in existing_books:
            new_book = Book(id=row['id'], title=row['Book'])
            db.session.add(new_book)
    
    db.session.commit()

    print("Books successfully added to the database.")

# Home page route, main recommendation function
@app.route('/', methods=['GET', 'POST'])
def index():
    recommendations = []
    user_favs = []
    user = None

    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            # Retrieve user's favorite books (pass the actual book objects)
            user_favs = [favorite.book for favorite in user.favorites if favorite.book]

    if request.method == 'POST':
        title = request.form['title']
        # Call the recommendation function to get similar books
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
    
    # Verify that the book exists in the database
    book = Book.query.get(book_id)
    if book is None:
        return "Book not found", 404

    # Add book to favorites if not already favorited
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
    
    # Find the favorite record in the database
    favorite = Favorite.query.filter_by(user_id=user_id, book_id=book_id).first()
    
    if favorite:
        # Remove the favorite from the database
        db.session.delete(favorite)
        db.session.commit()
    
    return redirect(url_for('index'))


# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
