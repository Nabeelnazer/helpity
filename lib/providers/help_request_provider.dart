import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class HelpRequest {
  final String id;
  final String userId;
  final String taskDescription;
  final Map<String, dynamic> location;
  final String status;
  final DateTime scheduledTime;
  final bool emergency;
  final String? volunteerId;
  final String? aiDescription;

  HelpRequest({
    required this.id,
    required this.userId,
    required this.taskDescription,
    required this.location,
    required this.status,
    required this.scheduledTime,
    required this.emergency,
    this.volunteerId,
    this.aiDescription,
  });

  factory HelpRequest.fromFirestore(DocumentSnapshot doc) {
    final data = doc.data() as Map<String, dynamic>;
    return HelpRequest(
      id: doc.id,
      userId: data['user_id'],
      taskDescription: data['task_description'],
      location: data['location'],
      status: data['status'],
      scheduledTime: (data['scheduled_time'] as Timestamp).toDate(),
      emergency: data['emergency'] ?? false,
      volunteerId: data['volunteer_id'],
      aiDescription: data['ai_description'],
    );
  }
}

class HelpRequestProvider with ChangeNotifier {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final String _apiBaseUrl = 'http://localhost:8000'; // Change in production
  List<HelpRequest> _requests = [];
  bool _isLoading = false;

  List<HelpRequest> get requests => _requests;
  bool get isLoading => _isLoading;

  Future<void> createHelpRequest({
    required String userId,
    required String taskDescription,
    required Map<String, dynamic> location,
    required DateTime scheduledTime,
    bool emergency = false,
  }) async {
    try {
      _isLoading = true;
      notifyListeners();

      final response = await http.post(
        Uri.parse('$_apiBaseUrl/api/help-requests'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'user_id': userId,
          'task_description': taskDescription,
          'location': location,
          'scheduled_time': scheduledTime.toIso8601String(),
          'emergency': emergency,
        }),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to create help request');
      }

      await loadRequests(userId: userId);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> loadRequests({
    required String userId,
    String? role,
  }) async {
    try {
      _isLoading = true;
      notifyListeners();

      final response = await http.get(
        Uri.parse('$_apiBaseUrl/api/help-requests?user_id=$userId&role=${role ?? "user"}'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body) as List;
        _requests = data.map((item) => HelpRequest.fromFirestore(
          item as DocumentSnapshot<Map<String, dynamic>>
        )).toList();
      } else {
        throw Exception('Failed to load help requests');
      }
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> respondToRequest({
    required String requestId,
    required String volunteerId,
    required String status,
  }) async {
    try {
      _isLoading = true;
      notifyListeners();

      final response = await http.post(
        Uri.parse('$_apiBaseUrl/api/volunteer-response'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'volunteer_id': volunteerId,
          'request_id': requestId,
          'status': status,
        }),
      );

      if (response.statusCode != 200) {
        throw Exception('Failed to respond to help request');
      }

      await loadRequests(userId: volunteerId, role: 'volunteer');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> updateFCMToken(String userId) async {
    try {
      final token = await FirebaseMessaging.instance.getToken();
      if (token != null) {
        await _firestore.collection('users').doc(userId).update({
          'fcm_token': token,
        });
      }
    } catch (e) {
      debugPrint('Error updating FCM token: $e');
    }
  }
}
