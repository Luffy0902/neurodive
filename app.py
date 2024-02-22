from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField,SelectField
from wtforms.validators import DataRequired
from flask import request
from sqlalchemy import or_


app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///neurodive.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

app.secret_key = 'your_secret_key'
bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120),unique=True,nullable=False)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    dob = db.Column(db.Date, nullable=True)  # Assuming date of birth is a date field
    password_hash = db.Column(db.String(120), nullable=False)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('posts', lazy=True))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    likes = db.relationship('Like', backref='post', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    post = db.relationship('Post', backref=db.backref('comments', lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


with app.app_context():
    db.create_all()

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()], render_kw={'class': 'form-control'})
    content = TextAreaField('Content', validators=[DataRequired()], render_kw={'class': 'form-control','rows': 8})
    category = SelectField('Category', choices=[
        ('General', 'General'),
        ('School', 'School'),
        ('Home life', 'Home life'),
        ('Hobbies', 'Hobbies'),
        ('Stress', 'Stress'),
        ('Relationships', 'Relationships'),
        ('Work', 'Work'),
    ], render_kw={'class': 'form-control'})
    submit = SubmitField('Post', render_kw={'class': 'btn btn-primary'})

class CommentForm(FlaskForm):
    content = TextAreaField('Add a Comment', validators=[DataRequired()])
    submit = SubmitField('Post')


@app.route('/')
def home():
    current_user = session.get('user')
    username = None

    if current_user:
        user_id = current_user.get('id')
        user = User.query.get(user_id)
        if user:
            username = user.username

    return render_template('home.html', current_user=current_user, username=username)




@app.route('/urgenthelp')
def urgenthelp():
    current_user = session.get('user')
    username = None
    if current_user:
        user_id = current_user.get('id')
        user = User.query.get(user_id)
        if user:
            username = user.username
    return render_template('urgenthelp.html', current_user=current_user, username=username)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']

        # Check if the identifier is an email or a username
        user = User.query.filter((User.email == identifier) | (User.username == identifier)).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            flash('Login successful', 'success')
            session['user'] = {'id': user.id, 'username': user.username}
            return redirect(url_for('home'))
        else:
            flash('Login failed. Please check your email or username and password.', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        username = request.form['username']
        dob_str = request.form['dob'] 
        password = request.form['password']
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
                if User.query.filter_by(username=username).first() :
                    flash('Username already exists. Please choose a different username.', 'error')
                if User.query.filter_by(email=email).first():
                    flash('Email already exists.', 'error')

        else:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()

                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                new_user = User(email=email, name=name, username=username, dob=dob, password_hash=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful. You can now log in.', 'success')
                return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/community', methods=['GET', 'POST'])
def community():
    if 'user' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))

    current_user = session['user']
    user_id = current_user.get('id')
    user = User.query.get(user_id)
    username = user.username if user else None

    # Fetch categories for the post form
    predefined_categories = [
        ('General', 'General'),
        ('School', 'School'),
        ('Home life', 'Home life'),
        ('Hobbies', 'Hobbies'),
        ('Stress', 'Stress'),
        ('Relationships', 'Relationships'),
        ('Work', 'Work'),
    ]

    # Fetch posts from the database
    categories = request.args.getlist('category')
    if categories:
        filters = [Post.category == category for category in categories]
        posts_query = Post.query.filter(or_(*filters))
    else:
        posts_query = Post.query

    # Sort posts by timestamp or likes
    sort_by = request.args.get('sort_by')
    if sort_by == 'likes':
        posts_query = posts_query.outerjoin(Like).group_by(Post.id).order_by(db.func.count(Like.id).desc())
    else:
        posts_query = posts_query.order_by(Post.timestamp.desc())

    posts = posts_query.all()

    # Handle post creation and comment addition
    post_form = PostForm()

    if request.method == 'POST':
        if post_form.validate_on_submit():
            new_post = Post(title=post_form.title.data,
                            content=post_form.content.data,
                            category=post_form.category.data,
                            user_id=user_id)
            db.session.add(new_post)
            db.session.commit()
            flash('Post created successfully.', 'success')
            return redirect(url_for('community'))

    return render_template('community.html', current_user=current_user, username=username,
                            posts=posts, post_form=post_form, predefined_categories=predefined_categories)


@app.route('/view_and_add_comments/<int:post_id>', methods=['GET', 'POST'])
def view_and_add_comments(post_id):
    current_user = session.get('user')
    username = None
    if current_user:
        user_id = current_user.get('id')
        user = User.query.get(user_id)
        if user:
            username = user.username

    if 'user' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))

    current_user = session.get('user')
    user_id = current_user.get('id')
    user = User.query.get(user_id)

    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('community'))

    post = Post.query.get(post_id)

    if not post:
        flash('Post not found.', 'error')
        return redirect(url_for('community'))

    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp.desc()).all()

    comment_form = CommentForm()

    if comment_form.validate_on_submit():
        new_comment = Comment(content=comment_form.content.data, post=post, user=user)
        db.session.add(new_comment)
        db.session.commit()
        flash('Comment added successfully.', 'success')
        return redirect(url_for('view_and_add_comments', post_id=post.id))

    return render_template('view_and_add_comments.html', current_user=current_user, username=username, post=post, comments=comments, comment_form=comment_form)


@app.route('/like/<int:post_id>', methods=['GET'])
def like_post(post_id):
    if 'user' not in session:
        flash('Please log in to like a post.', 'error')
        return redirect(url_for('login'))

    current_user = session['user']
    user_id = current_user.get('id')

    post = Post.query.get(post_id)
    if not post:
        flash('Post not found.', 'error')
        return redirect(url_for('home'))

    # Check if the user has already liked the post
    like = Like.query.filter_by(post_id=post_id, user_id=user_id).first()
    if like:
        # User already liked the post, so unlike it
        db.session.delete(like)
        db.session.commit()
        flash('You unliked the post.', 'success')
    else:
        # User hasn't liked the post yet, so like it
        new_like = Like(post_id=post_id, user_id=user_id)
        db.session.add(new_like)
        db.session.commit()
        flash('You liked the post.', 'success')

    return redirect(url_for('home'))


@app.route('/Sensory_Calming_Activites')
def Sensory_Calming_Activites():
    current_user = session.get('user')
    username = None
    if current_user:
        user_id = current_user.get('id')
        user = User.query.get(user_id)
        if user:
            username = user.username
    return render_template('Sensory_Calming_Activites.html', current_user=current_user, username=username)

@app.route('/Assistance')
def Assistance():
    current_user = session.get('user')
    username = None
    if current_user:
        user_id = current_user.get('id')
        user = User.query.get(user_id)
        if user:
            username = user.username
    return render_template('Assistance.html', current_user=current_user, username=username)

@app.route('/profile')
def profile():
    if 'user' not in session:
        flash('Please log in to access your profile.', 'error')
        return redirect(url_for('login'))

    current_user = session['user']
    user_id = current_user.get('id')
    user = User.query.get(user_id)
    username=user.username
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('home'))

    return render_template('profile.html', current_user=current_user, user=user,username=username)


# Add this route for editing user profile
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user' not in session:
        flash('Please log in to edit your profile.', 'error')
        return redirect(url_for('login'))

    current_user = session['user']
    user_id = current_user.get('id')
    user = User.query.get(user_id)
    username=user.username

    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Update user information
        user.email = request.form['email']
        user.name = request.form['name']
        user.dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))

    return render_template('editprofile.html', current_user=current_user, user=user,username=username)

@app.route("/About", methods=['GET', 'POST'])
def About():
    current_user = session.get('user')
    username = None
    if current_user:
        user_id = current_user.get('id')
        user = User.query.get(user_id)
        if user:
            username = user.username
    return render_template('About.html', current_user=current_user, username=username)
if __name__ == '__main__':
    app.run(debug=True)