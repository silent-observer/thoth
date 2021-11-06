import os, string
from flask import Flask, g, request, session, render_template, abort
from flask.helpers import url_for
from neo4j import GraphDatabase
from neo4j.time import DateTime

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
            register_date = DateTime.now()
            db.run(
                r'CREATE (n:User {username:$username, pass_hash:$pass_hash, register_date:$register_date})',
                username=username, pass_hash=pass_hash, register_date=register_date
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
        date = DateTime.now()
 
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
                r'MATCH (U:User {username:$username}) CREATE (Q:Question {title:$title, question:$question, id: $id, date: $date, votes: 0}) <-[r:ASKED]-(U)',
                title=title, question=question, username = username, id=id, date=date
            )
            return redirect(url_for('q', id=id))
   
    return form_text
 
 
@app.route("/q/<id>",methods=['POST', 'GET'])
def q(id):
    with get_db().session() as db:
        logged_in = 'username' in session
        if request.method == 'POST':
            if not logged_in:
                return redirect(url_for('q', id=id))
            
            username = session['username']
            date = DateTime.now()

            if 'q_id' in request.form:
                comment = request.form['comment']
                db.run(
                    r'MATCH (U:User {username:$username}), (Q:Question {id:$id}) CREATE (Q)<-[:TO]-(C:Comment {comment:$comment, date:$date}) <-[:COMMENTED]-(U)',
                    username = username, id=id, comment=comment, date=date
                )
            elif 'a_id' in request.form:
                comment = request.form['comment']
                a_id = request.form['a_id']
                db.run(
                    r'MATCH (U:User {username:$username}), (A:Answer) WHERE id(A) = $a_id CREATE (A)<-[:TO]-(C:Comment {comment:$comment, date:$date})<-[:COMMENTED]-(U)',
                    username = username, a_id=int(a_id), comment=comment, date=date
                )
            else:
                answer = request.form['answer']
                db.run(
                    r'MATCH (U:User {username:$username}), (Q:Question {id:$id}) CREATE (Q)<-[:TO]-(A:Answer {answer:$answer, date:$date, votes: 0}) <-[:ANSWERED]-(U)',
                    username = username, id=id, answer=answer, date=date
                )
            return redirect(url_for('q', id=id))

        result = db.run(
        r'MATCH (Q:Question {id: $id})<-[r:ASKED]-(U:User) return Q,U',id=id
        ).single()
        if result is None:
            abort(404)

        #словарь где Q - переменная с узлом, а title - поле/свойство во узла
        data = {
            'question' : {
                'title': result['Q']['title'],
                'text': result['Q']['question'],
                'date': result['Q']['date'],
                'votes': result['Q']['votes'],
                'author': {'name': result['U']['username']},
                'comments': []
            }, 
            'answers': []
        }

        result = db.run(
        r'MATCH (Q:Question {id: $id})<-[:TO]-(C:Comment)<-[:COMMENTED]-(U:User) return C,U ORDER BY C.date',id=id
        )
        for r in result:
            data['question']['comments'].append({
                'text': r['C']['comment'],
                'author': {'name': r['U']['username']}
            })

        result = db.run(
        r'MATCH (Q:Question {id: $id})<-[:TO]-(A:Answer)<-[:ANSWERED]-(U:User) return A,U,[(CU:User)-[:COMMENTED]->(C:Comment)-[:TO]->(A) | [C.date, CU.username, C.comment]] AS comments',id=id
        )
        for r in result:
            answer = {
                'id': r['A'].id,
                'text': r['A']['answer'],
                'date': r['A']['date'],
                'author': {'name': r['U']['username']},
                'votes': r['A']['votes'],
                'comments': [{
                        'date': comment[0],
                        'text': comment[2],
                        'author': {'name': comment[1]}
                    } for comment in sorted(r['comments'])]
            }
            data['answers'].append(answer)

        return render_template('q.html', data=data, logged_in=logged_in)
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

