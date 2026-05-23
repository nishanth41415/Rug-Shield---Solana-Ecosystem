const RugShieldSDK = require('./index.js');

const sdk = new RugShieldSDK();

async function test() {
  console.log('Testing RugShield SDK...\n');
  
  // Test score endpoint
  console.log('1. Testing score() method:');
  try {
    const score = await sdk.score('7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU');
    console.log('✅ Score:', score);
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
  
  // Test stream endpoint
  console.log('\n2. Testing stream() method:');
  console.log('Listening for high-risk tokens (score >= 70)...\n');
  
  const ws = sdk.stream((token) => {
    console.log('🚨 HIGH RISK TOKEN DETECTED:');
    console.log(`   Mint: ${token.mint}`);
    console.log(`   Score: ${token.score}`);
    console.log(`   Risk: ${token.riskLevel}\n`);
  }, 70);
  
  // Run for 30 seconds then close
  setTimeout(() => {
    ws.close();
    console.log('✅ Test complete');
    process.exit(0);
  }, 30000);
}

test();
