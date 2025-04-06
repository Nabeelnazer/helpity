const express = require('express');
const router = express.Router();
const { authenticateUser } = require('../middleware/auth.middleware');

// Protected route example
router.get('/profile', authenticateUser, async (req, res) => {
  try {
    // req.user contains the decoded token information
    const userId = req.user.uid;
    // Access Firestore using req.db
    const userDoc = await req.db.collection('users').doc(userId).get();
    
    if (!userDoc.exists) {
      return res.status(404).json({ error: 'User not found' });
    }
    
    res.json(userDoc.data());
  } catch (error) {
    res.status(500).json({ error: 'Server error' });
  }
});

module.exports = router;