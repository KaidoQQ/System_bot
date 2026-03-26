from flask import Flask,render_template
import json
import sqlite3

app = Flask(__name__)

@app.route("/user/<int:id>")
def info_user(id):
  conn = sqlite3.connect('computers.db', check_same_thread=False)
  cursor = conn.cursor()

  cursor.execute('SELECT computers_data FROM users WHERE user_id = ?',(id,))

  result = cursor.fetchone()

  conn.close()

  if result:
    info = json.loads(result[0])

  else:
    return "❌ Error, no users with this id!"


  return render_template('stats.html', id_user=info, count=len(info)) 


if __name__ == "__main__":
  app.run(debug=True)