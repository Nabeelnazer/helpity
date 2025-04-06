const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { db, admin } = require('./config/firebase.config');
const testRoutes = require('./routes/test.routes');
const protectedRoutes = require('./routes/protected.routes');
const userRoutes = require('./routes/user.routes');

// Load environment variables
dotenv.config();

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Make Firebase instances available in the request object
app.use((req, res, next) => {
  req.db = db;
  req.admin = admin;
  next();
});

// Routes
app.use('/api/test', testRoutes);
app.use('/api/protected', protectedRoutes);
app.use('/api/users', userRoutes);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!', details: err.message });
});

const PORT = process.env.PORT || 8000;
const HOST = process.env.HOST || '0.0.0.0';

app.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
});

module.exports = app;