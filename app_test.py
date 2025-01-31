from flask import Flask, render_template_string, redirect, url_for, request
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key in production

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to 'login' view if unauthorized

# Hardcoded user data
USERS = {
    'testuser': {
        'id': '1',
        'username': 'testuser',
        'password': 'password123'  # In production, passwords should be hashed!
    }
}

# User model
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# User loader callback
@login_manager.user_loader
def load_user(user_id):
    for user in USERS.values():
        if user['id'] == user_id:
            return User(user['id'], user['username'], user['password'])
    return None

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = USERS.get(username)
        if user_data and user_data['password'] == password:
            user = User(user_data['id'], user_data['username'], user_data['password'])
            login_user(user)
            return redirect(url_for('protected'))
        else:
            return 'Invalid username or password', 401

    # Simple login form
    return render_template_string('''
        <h2>Login</h2>
        <form method="post">
            <input type="text" name="username" placeholder="Username" required><br><br>
            <input type="password" name="password" placeholder="Password" required><br><br>
            <input type="submit" value="Login">
        </form>
    ''')

# Protected route
@app.route('/protected')
@login_required
def protected():
    return f'Hello, {current_user.username}! You are logged in.'

# Home route
@app.route('/')
def home():
    return redirect(url_for('protected'))

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return 'You have been logged out.'

if __name__ == '__main__':
    app.run(debug=True)
