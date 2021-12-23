import os, string
from flask import Flask, g, request, session, render_template, abort
from flask.helpers import url_for
from neo4j import GraphDatabase, unit_of_work
from neo4j.time import Date, DateTime

import bcrypt, base64
from werkzeug.utils import redirect
import random, atexit
from apscheduler.schedulers.background import BackgroundScheduler

neo4j_pass = os.environ.get('NEO4J_PASS')
neo4j_uri = 'neo4j+s://1f59f68c.databases.neo4j.io'

def update_recommendations():
    with GraphDatabase.driver(neo4j_uri, auth=('neo4j', neo4j_pass)) as local_db:
        with local_db.session() as db:
            db.run(r'''
                MATCH (a:Question)<-[:VIEWED]-(u:User)-[:VIEWED]->(b:Question)
                WHERE id(a) < id(b) AND (a.needs_update OR b.needs_update)
                WITH a, b, count(u) as aAndB
                WITH a, b, aAndB, toFloat(aAndB)/toFloat(a.views+b.views-aAndB) as j
                WHERE j > 0.15
                MERGE (a)-[s:SIMILAR]-(b)
                SET s.jaccard = j, a.needs_update = false, b.needs_update = false;
            ''')
            print('Updated recommendations!')

sched = BackgroundScheduler(daemon=True)
sched.add_job(update_recommendations, 'interval', minutes=60)
sched.start()

atexit.register(lambda: sched.shutdown(wait=False))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

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
    logged_in = 'username' in session
    with get_db().session() as db:
        questions = []
        if logged_in:
            username = session['username']
            result = db.run(r'''
                MATCH (u:User {username:$username})
                MATCH (u)-[v:VIEWED]->(qv:Question)
                MATCH (qv)-[s:SIMILAR]-(qs:Question)
                WHERE NOT (u)-[:VIEWED]->(qs)
                WITH u, qs, sum(s.jaccard) as j
                MATCH (a:User)-[:ASKED]->(qs)-[:CORRESPONDS]->(d:Discipline)
                OPTIONAL MATCH (u)-[voted:VOTED]->(qs)
                RETURN a, qs, d, voted, j
                ORDER BY j DESC
                LIMIT 50''', username=username
            )
        else:
            result = db.run(r'''
                MATCH (qs:Question)
                WITH qs, duration.inSeconds(datetime(), qs.date).seconds as secondsPast
                WITH qs, qs.views + qs.votes * 2 - secondsPast + 50.0 / (1.0 + 0.00001 * secondsPast) as j
                MATCH (a:User)-[:ASKED]->(qs)-[:CORRESPONDS]->(d:Discipline)
                RETURN a, qs, d, j
                ORDER BY j DESC
                LIMIT 50'''
            )
        for r in result:
            questions.append({
                'id': r['qs']['id'],
                'title': r['qs']['title'],
                'text': r['qs']['question'],
                'date': r['qs']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
                'votes': r['qs']['votes'],
                'current_vote': r['voted']['vote'] if 'voted' in r and r['voted'] is not None else 0,
                'author': {'name': r['a']['username']},
                'discipline': r['d']['name']
            })

        data = {
            'questions': questions
        }
    return render_template('feed.html', data=data, logged_in=logged_in)

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
    

    error = None
    if request.method == 'POST':
        title = request.form['title']
        question = request.form['question']
        username = session['username']
        discipline = request.form['discipline']
        date = DateTime.now()

        if len(title) < 10 or len(title) > 100:
            error = "Заголовок должен содержать не менее 10 и не более 100 символов."
        if len(question) < 10 or len(question) > 2000:
            error = "Текст вопроса должен содержать не менее 10 и не более 2000 символов."
        if discipline is None or discipline == "":
            error = "Выберите предмет и дисциплину."

        if error is None:
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
                    r'MATCH (U:User {username:$username}), (D:Discipline {name:$discipline}) CREATE (D)<-[:CORRESPONDS]-(Q:Question {title:$title, question:$question, id: $id, date: $date, votes: 0, views: 0, needs_update: false})<-[r:ASKED]-(U)',
                    title=title, question=question, username = username, id=id, date=date, discipline=discipline
                )
                return redirect(url_for('q', id=id))
   

    with get_db().session() as db:
        result = db.run(r'MATCH (s:Subject)-[:CONTAINS]->(d:Discipline) RETURN s, d')
        data = {}
        for r in result:
            if r['s']['name'] not in data:
                data[r['s']['name']] = []
            data[r['s']['name']].append(r['d']['name'])
    return render_template('question.html', data=data, error=error)


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

        username = session['username'] if 'username' in session else ''

        result = db.run(
        r'''
            MATCH (D:Discipline)<-[:CORRESPONDS]-(Q:Question {id: $id})<-[r:ASKED]-(U:User) 
            OPTIONAL MATCH (:User {username:$username})-[v:VOTED]->(Q) 
            RETURN Q,U,D,v''',id=id, username=username
        ).single()
        if result is None:
            abort(404)

        data = {
            'question' : {
                'id': id,
                'title': result['Q']['title'],
                'text': result['Q']['question'],
                'date': result['Q']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
                'votes': result['Q']['votes'],
                'current_vote': result['v']['vote'] if result['v'] is not None else 0,
                'author': {'name': result['U']['username']},
                'discipline': result['D']['name'],
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
        r'MATCH (Q:Question {id: $id})<-[:TO]-(A:Answer)<-[:ANSWERED]-(U:User) OPTIONAL MATCH (:User {username:$username})-[v:VOTED]->(A) return A,U,[(CU:User)-[:COMMENTED]->(C:Comment)-[:TO]->(A) | [C.date, CU.username, C.comment]] AS comments,v',id=id, username=username
        )
        for r in result:
            answer = {
                'id': r['A'].id,
                'text': r['A']['answer'],
                'date': r['A']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
                'author': {'name': r['U']['username']},
                'votes': r['A']['votes'],
                'current_vote': r['v']['vote'] if r['v'] is not None else 0,
                'comments': [{
                    'date': comment[0].to_native().strftime('%d.%m.%Y %H:%M'),
                    'text': comment[2],
                    'author': {'name': comment[1]}
                } for comment in sorted(r['comments'])]
            }
            data['answers'].append(answer)

        if logged_in:
            db.run(r'''
                MATCH (Q:Question {id: $id}), (U:User {username:$username}) 
                MERGE (U)-[r:VIEWED]->(Q)
                ON CREATE
                SET Q.views = Q.views + 1, Q.needs_update = true''',
                id=id, username=username
            )

        return render_template('q.html', data=data, logged_in=logged_in)
        # return f'''<h1>{title}</h1>'''    
# HTML-собрать и на странице поста указать автора поста

@app.route("/votes",methods=['POST'])
def votes():
    @unit_of_work(timeout=5)
    def trans_func(tx, form, username):
        vote = int(form['vote'])
        if (vote not in [-1, 0, 1]): return
        if 'q_id' in form:
            q_id = form['q_id']
            result = tx.run(
                r'MATCH (U:User {username:$username})-[v:VOTED]->(Q:Question {id:$id}) RETURN v',
                username = username, id=q_id
            ).single()
            if result is None:
                old_vote = 0
            else:
                old_vote = result['v']['vote']
            tx.run(
                r'MATCH (U:User {username:$username})-[v1:VOTED]->(Q:Question {id:$id}) DELETE v1',
                username = username, id=q_id
            )
            if vote != 0:
                tx.run(
                    r'MATCH (U:User {username:$username}), (Q:Question {id:$id}) CREATE (U)-[v2:VOTED {vote:$vote}]->(Q)',
                    username = username, id=q_id, vote=vote
                )
            tx.run(
                r'MATCH (Q:Question {id:$id}) SET Q.votes = Q.votes + $inc',
                username = username, id=q_id, inc=vote - old_vote
            )
        elif 'a_id' in form:
            a_id = form['a_id']
            result = tx.run(
                r'MATCH (U:User {username:$username})-[v:VOTED]->(A:Answer) WHERE id(A) = $a_id RETURN v',
                username = username, a_id=int(a_id)
            ).single()
            if result is None:
                old_vote = 0
            else:
                old_vote = result['v']['vote']
            tx.run(
                r'MATCH (U:User {username:$username})-[v1:VOTED]->(A:Answer) WHERE id(A) = $a_id DELETE v1',
                username = username, a_id=int(a_id)
            )
            if vote != 0:
                tx.run(
                    r'MATCH (U:User {username:$username}), (A:Answer) WHERE id(A) = $a_id CREATE (U)-[v2:VOTED {vote:$vote}]->(A)',
                    username = username, a_id=int(a_id), vote=vote
                )
            tx.run(
                r'MATCH (A:Answer) WHERE id(A)=$a_id SET A.votes = A.votes + $inc',
                username = username, a_id=int(a_id), inc=vote - old_vote
            )
    
    with get_db().session() as db:
        logged_in = 'username' in session
        if logged_in:
            db.write_transaction(trans_func, request.form, session['username'])
    return ''

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

