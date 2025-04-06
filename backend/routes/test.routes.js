const express = require('express');
const { admin } = require('../config/firebase.config');
const router = express.Router();

router.get('/firebase-test', async (req, res) => {
  try {
    const testDoc = await req.db.collection('test').doc('test').set({
      timestamp: admin.firestore.FieldValue.serverTimestamp()
    });
    res.json({ message: 'Firebase is properly configured!' });
  } catch (error) {
    res.status(500).json({ error: 'Firebase configuration error', details: error.message });
  }
});

module.exports = router;