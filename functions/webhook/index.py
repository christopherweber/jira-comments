import os
import requests
from flask_lambda import FlaskLambda
from flask import request, jsonify

# Check if we're running in a local development environment
if os.environ.get('FLASK_ENV') == 'development':
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file

app = FlaskLambda(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    incident_id = data.get("data", {}).get("incident", {}).get("id")

    if not incident_id:
        return jsonify({"error": "Incident ID not found in payload"}), 400

    # Authorization for FireHydrant
    firehydrant_token = os.getenv("FIREHYDRANT_TOKEN")
    headers = {"Authorization": f"Bearer {firehydrant_token}"}
    incident_details_url = f"https://api.firehydrant.io/v1/incidents/{incident_id}"
    incident_response = requests.get(incident_details_url, headers=headers)
    incident_details = incident_response.json()

    last_note_body = incident_details.get("data", [{}])[0].get("last_note", {}).get("body")
    if not last_note_body:
        return jsonify({"error": "Last note body not found in incident details"}), 400

    # JIRA Authentication and Request
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_TOKEN")
    jira_url = "https://spaceshipco.atlassian.net/rest/api/3/issue/AC-75/comment"
    jira_auth = (jira_email, jira_token)
    jira_headers = {"Content-Type": "application/json"}
    jira_payload = {
        "body": {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "text": last_note_body,
                            "type": "text"
                        }
                    ]
                }
            ]
        }
    }

    jira_response = requests.post(jira_url, json=jira_payload, auth=jira_auth, headers=jira_headers)
    if jira_response.status_code != 201:
        return jsonify({"error": "Failed to create Jira comment", "details": jira_response.text}), 400

    return jsonify({"message": "Jira comment created successfully"}), 200