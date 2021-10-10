import os, string
from flask import Flask, g, request, session
from flask.helpers import url_for
from neo4j import GraphDatabase
import bcrypt, base64
from werkzeug.utils import redirect
import random
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

neo4j_pass = os.environ.get('NEO4J_PASS')
neo4j_uri = 'neo4j+s://1f59f68c.databases.neo4j.io'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = GraphDatabase.driver(
            neo4j_uri, auth=('neo4j', neo4j_pass))
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/")
def main():
    names = []
    with get_db().session() as db:
        result = db.run('MATCH (n:Person) RETURN n')
        for r in result:
            names.append(r['n']['name'])
    if 'username' in session:
        text = f'''
            <p>You are logged in as "{session["username"]}".
            <a href={url_for('logout')}>Logout</a></p>
            '''
    else:
        text = f'''
            <p>You are not logged in.</p>
            <p><a href={url_for('login')}>Login</a></p>
            <p><a href={url_for('register')}>Register</a></p>
            '''
    return text + "<p>People:<br>" + '<br>'.join(names) + "</p>"

@app.route("/users")
def users():
    names = []
    with get_db().session() as db:
        result = db.run('MATCH (n:User) RETURN n')
        for r in result:
            names.append(r['n']['username'])
    return "<p>Users:<br>" + '<br>'.join(names) + "</p>"


allowed_username_characters = set(
    string.ascii_letters + string.digits + '.-_'
)
def is_valid(username):
    return set(username) <= allowed_username_characters

@app.route("/register", methods=['POST', 'GET'])
def register():
    form_text = '''
        <p>Registration form:</p>
        <form method="post">
            <label for="username">Username:</label><br>
            <input type="text" id="username" name="username"><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password"><br>
            <input type="submit" value="Submit">
        </form>
        '''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not is_valid(username):
            return '<p>Username can only contain Latin letters, digits and ".", "-", "_" symbols.</p>' + form_text
        
        with get_db().session() as db:
            result = db.run(
                r'MATCH (n:User {username:$username}) RETURN n',
                username=username
                ).single()
            if result is not None:
                return '<p>Username already used, please pick another one</p>' + form_text
            pass_hash = base64.b64encode(bcrypt.hashpw(
                password.encode('utf-8'), bcrypt.gensalt()
                )).decode('ascii')
            db.run(
                r'CREATE (n:User {username:$username, pass_hash:$pass_hash})',
                username=username, pass_hash=pass_hash
            )
            return redirect(url_for('users'))
    else:
        return form_text

@app.route("/login", methods=['POST', 'GET'])
def login():
    if 'username' in session:
        return f'''
            <p>Already logged in as "{session["username"]}"".
            <a href={url_for('logout')}>Logout</a></p>
            '''

    form_text = '''
        <p>Login:</p>
        <form method="post">
            <label for="username">Username:</label><br>
            <input type="text" id="username" name="username"><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password"><br>
            <input type="submit" value="Submit">
        </form>
        '''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not is_valid(username):
            return '<p>Username can only contain Latin letters, digits and ".", "-", "_" symbols.</p>' + form_text
        
        with get_db().session() as db:
            result = db.run(
                r'MATCH (n:User {username:$username}) RETURN n',
                username=username
                ).single()
            if result is None:
                return '<p>No user with such username</p>' + form_text
            pass_hash = base64.b64decode(result['n']['pass_hash'])
            if bcrypt.hashpw(password.encode('utf-8'), pass_hash) == pass_hash:
                session['username'] = username
                return redirect(url_for('main'))
            else:
                return '<p>Invalid password!</p>' + form_text
    else:
        return form_text

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('main'))

@app.route("/question", methods=['POST', 'GET'])

def question():
    if 'username' not in session:
        return redirect(url_for('login'))
       
    form_text = '''
       <p>Question form:</p>
       <form method="post">
           <label for="title">title:</label><br>
           <input type="text" id="title" name="title"><br>
           <label for="question">Question:</label><br>
           <textarea id="question" name="question"></textarea>
           <br>
           <input type="submit" value="Submit">
       </form>
       '''
    if request.method == 'POST':
        title = request.form['title']
        question = request.form['question']
        username = session['username']
 
        with get_db().session() as db:
           
            while (True):
                id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                result = db.run(
                r'MATCH (Q:Question {id: $id}) RETURN Q',
                id = id
                ).single()
                if result is None:
                    break
            db.run(
                r'MATCH (U:User {username:$username}) CREATE (Q:Question {title:$title, question:$question, id: $id}) <-[r:ASKED]-(U)',
                title=title, question=question, username = username, id=id
            )
            return redirect(url_for('q', id=id))
   
    return form_text
 
 
@app.route("/q/<id>",methods=['POST', 'GET'])
def q(id):
    with get_db().session() as db:
        result = db.run(
        r'MATCH (Q:Question {id: $id})<-[r:ASKED]-(U:User) return Q,U',id=id
        ).single()
        if result is None:
            abort(404)
        title = result['Q']['title'] #словарь где Q - переменная с узлом, а title - поле/свойство во узла
        question =result['Q']['question']
        username = result['U']['username']

        result = db.run(
        r'MATCH (Q:Question {id: $id})<-[:TO]-(A:Answer)<-[:ANSWERED]-(U:User) return A,U',id=id
        )
        answers = []
        for r in  result:
            string = f"{r['U']['username']}: {r['A']['answer']}"
            answers.append(string)
        a_text = "<br>".join(answers)
        q_text = f'''
        <p>Question:</p>
        <h1>{username}</h1>
        <h1>{title}</h1>
        <p>{question}</p>'''
        form_text=f'''
        <form method="post">
           <label for="answer">Answer:</label><br>
           <textarea id="answer" name="answer"></textarea>
           <br>
           <input type="submit" value="Submit">
       </form>
        '''
        if 'username' not in session:
            return q_text+a_text
        if request.method == 'POST':
            answer = request.form['answer']
            username = session['username']
            db.run(
                r'MATCH (U:User {username:$username}), (Q:Question {id:$id}) CREATE (Q)<-[:TO]-(A:Answer {answer:$answer}) <-[:ANSWERED]-(U)',
                username = username, id=id, answer=answer
            )
            return redirect(url_for('q', id=id))

        return q_text+form_text+a_text
        # return f'''<h1>{title}</h1>'''    
# HTML-собрать и на странице поста указать автора поста

@app.route("/search")
def search():
    search_text = request.args.get('s', '')
    form_text = f'''
    <form method="get">
        <input type="text" id="s" name="s" value="{search_text}">
        <input type="submit" value="Find">
    </form>
    '''
    if search_text == '':
        return form_text
    
    text = '<h2>Search results</h2>'

    with get_db().session() as db:
        result = db.run(
            'CALL db.index.fulltext.queryNodes("titlesAndTexts", $text) YIELD node, score RETURN node, score LIMIT 50', text=search_text
        )

        result_texts = []
        for r in result:
            url = url_for('q', id=r['node']['id'])
            title = r['node']['title']
            question = r['node']['question']
            if len(question) > 30:
                question = question[:30] + '...'

            result_texts.append(f'''
                <li><b><a href={url}>{title}</a></b><br>
                {question}
                </li>
            ''')
        if len(result_texts) == 0:
            text += '<p>Nothing was found</p>'
        else:
            text += '<ul>' + ''.join(result_texts) + '</ul>'
        return form_text + text

