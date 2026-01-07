from flask import Blueprint, render_template, request

# Create a Blueprint for views
views = Blueprint("views", __name__)

@views.route("/")
def home():
    """Home page route."""
    return render_template("index.html", title="Home Page")

@views.route("/greet", methods=["GET", "POST"])
def greet():
    """Route that greets the user."""
    if request.method == "POST":
        name = request.form.get("name", "Guest").strip()
        if not name:
            name = "Guest"
        return f"<h2>Hello, {name}!</h2>"
    return '''
        <form method="POST">
            <input type="text" name="name" placeholder="Enter your name">
            <button type="submit">Greet Me</button>
        </form>
    '''
