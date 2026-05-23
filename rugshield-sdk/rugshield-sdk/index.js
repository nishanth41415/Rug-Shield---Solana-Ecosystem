const axios = require('axios');
const WebSocket = require('ws');

class RugShieldSDK {
  constructor(apiUrl = 'http://localhost:3000') {
    this.apiUrl = apiUrl;
  }

  async score(mintAddress) {
    try {
      const response = await axios.get(`${this.apiUrl}/score/${mintAddress}`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch score: ${error.message}`);
    }
  }

  stream(callback, threshold = 70) {
    const wsUrl = this.apiUrl.replace('http', 'ws') + '/stream';
    const ws = new WebSocket(wsUrl);

    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data);
        if (message.event === 'new_token' && message.data.score >= threshold) {
          callback(message.data);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    });

    ws.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    return ws;
  }
}

module.exports = RugShieldSDK;
