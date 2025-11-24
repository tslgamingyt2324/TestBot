from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot is WORKING on Render! ✅"

@app.route('/test')
def test():
    return "Test page is working! 🎉"

@app.route('/webhook', methods=['POST'])
def webhook():
    return "Webhook received! ✅"

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)