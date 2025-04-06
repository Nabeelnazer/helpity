const express = require('express');
const router = express.Router();
const { authenticateUser } = require('../middleware/auth.middleware');

// User registration
router.post('/register', async (req, res) => {
  try {
    const { uid, email, displayName, userType } = req.body;
    
    const userRef = req.db.collection('users').doc(uid);
    await userRef.set({
      email,
      displayName,
      userType, // 'helper' or 'helpseeker'
      createdAt: req.admin.firestore.FieldValue.serverTimestamp(),
      updatedAt: req.admin.firestore.FieldValue.serverTimestamp()
    });

    res.status(201).json({ message: 'User registered successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Registration failed', details: error.message });
  }
});

// Get user profile
router.get('/profile', authenticateUser, async (req, res) => {
  try {
    const userDoc = await req.db.collection('users').doc(req.user.uid).get();
    
    if (!userDoc.exists) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json(userDoc.data());
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch profile', details: error.message });
  }
});

// Update user profile
router.put('/profile', authenticateUser, async (req, res) => {
  try {
    const { displayName, phoneNumber, address } = req.body;
    
    await req.db.collection('users').doc(req.user.uid).update({
      displayName,
      phoneNumber,
      address,
      updatedAt: req.admin.firestore.FieldValue.serverTimestamp()
    });

    res.json({ message: 'Profile updated successfully' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to update profile', details: error.message });
  }
});

// Create help request
router.post('/help-requests', authenticateUser, async (req, res) => {
  try {
    const { title, description, location, urgency } = req.body;
    
    const helpRequestRef = req.db.collection('helpRequests').doc();
    await helpRequestRef.set({
      userId: req.user.uid,
      title,
      description,
      location,
      urgency,
      status: 'open',
      createdAt: req.admin.firestore.FieldValue.serverTimestamp(),
      updatedAt: req.admin.firestore.FieldValue.serverTimestamp()
    });

    res.status(201).json({ 
      message: 'Help request created successfully',
      requestId: helpRequestRef.id
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to create help request', details: error.message });
  }
});

// Get user's help requests
router.get('/help-requests', authenticateUser, async (req, res) => {
  try {
    const helpRequestsSnapshot = await req.db
      .collection('helpRequests')
      .where('userId', '==', req.user.uid)
      .orderBy('createdAt', 'desc')
      .get();

    const helpRequests = [];
    helpRequestsSnapshot.forEach(doc => {
      helpRequests.push({
        id: doc.id,
        ...doc.data()
      });
    });

    res.json(helpRequests);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch help requests', details: error.message });
  }
});

module.exports = router;