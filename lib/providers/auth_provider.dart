import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class AuthProvider with ChangeNotifier {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  User? _user;
  String? _userRole;
  bool _isLoading = false;

  AuthProvider() {
    _auth.authStateChanges().listen((User? user) {
      _user = user;
      if (user != null) {
        _loadUserRole();
      }
      notifyListeners();
    });
  }

  bool get isAuthenticated => _user != null;
  bool get isLoading => _isLoading;
  String? get userRole => _userRole;
  String? get userId => _user?.uid;

  Future<void> _loadUserRole() async {
    try {
      final doc = await _firestore.collection('users').doc(_user!.uid).get();
      _userRole = doc.data()?['role'];
      notifyListeners();
    } catch (e) {
      debugPrint('Error loading user role: $e');
    }
  }

  Future<void> signIn(String email, String password) async {
    try {
      _isLoading = true;
      notifyListeners();

      await _auth.signInWithEmailAndPassword(
        email: email,
        password: password,
      );
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> register({
    required String email,
    required String password,
    required String fullName,
    required String role,
    String? phone,
  }) async {
    try {
      _isLoading = true;
      notifyListeners();

      // Create auth user
      final userCredential = await _auth.createUserWithEmailAndPassword(
        email: email,
        password: password,
      );

      // Create user profile
      await _firestore.collection('users').doc(userCredential.user!.uid).set({
        'email': email,
        'fullName': fullName,
        'role': role,
        'phone': phone,
        'createdAt': FieldValue.serverTimestamp(),
      });

      _userRole = role;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> signOut() async {
    try {
      await _auth.signOut();
      _userRole = null;
    } catch (e) {
      debugPrint('Error signing out: $e');
    }
  }

  Future<void> updateProfile({
    String? fullName,
    String? phone,
  }) async {
    try {
      _isLoading = true;
      notifyListeners();

      final updates = <String, dynamic>{};
      if (fullName != null) updates['fullName'] = fullName;
      if (phone != null) updates['phone'] = phone;

      await _firestore.collection('users').doc(_user!.uid).update(updates);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
