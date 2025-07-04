from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime
import os

app = Flask(__name__)


client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017'))
db = client['github_actions']
collection = db['events']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/events', methods=['GET'])
def get_events():
    events = list(collection.find().sort('timestamp', -1).limit(10))
    for event in events:
        event['_id'] = str(event['_id'])
    return jsonify(events)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    event_type = request.headers.get('X-GitHub-Event')

    event_data = {
        'timestamp': datetime.utcnow(),
        'author': None,
        'action': None,
        'from_branch': None,
        'to_branch': None
    }

    if event_type == 'push':
        event_data.update({
            'author': data['pusher']['name'],
            'action': 'PUSH',
            'to_branch': data['ref'].split('/')[-1]
        })

    elif event_type == 'pull_request':
        pr_data = data['pull_request']
        if data['action'] in ['opened', 'reopened']:
            event_data.update({
                'author': pr_data['user']['login'],
                'action': 'PULL_REQUEST',
                'from_branch': pr_data['head']['ref'],
                'to_branch': pr_data['base']['ref']
            })

    elif event_type == 'pull_request' and data['action'] == 'closed' and data['pull_request']['merged']:
        
        pr_data = data['pull_request']
        event_data.update({
            'author': pr_data['user']['login'],
            'action': 'MERGE',
            'from_branch': pr_data['head']['ref'],
            'to_branch': pr_data['base']['ref']
        })

    else:
        return jsonify({"status": "ignored"}), 200

    collection.insert_one(event_data)
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(debug=True)
