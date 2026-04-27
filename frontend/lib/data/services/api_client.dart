import 'dart:convert';
import 'dart:io' show Platform;
import 'package:http/http.dart' as http;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart' show kIsWeb;

class ApiException implements Exception {
  final int statusCode;
  final String message;
  
  ApiException(this.statusCode, this.message);
  
  @override
  String toString() => 'ApiException: [$statusCode] $message';
}

class ApiClient {
  final http.Client _client = http.Client();
  
  String get baseUrl {
    if (kIsWeb) {
      return 'http://localhost:8000/api/v1';
    }
    if (Platform.isAndroid) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    return 'http://localhost:8000/api/v1'; // Windows, macOS, iOS simulator
  }

  Future<dynamic> get(String path, {String? token}) async {
    final response = await _client.get(
      Uri.parse('$baseUrl$path'),
      headers: _buildHeaders(token),
    );
    return _processResponse(response);
  }

  Future<dynamic> post(String path, {Map<String, dynamic>? body, String? token}) async {
    final response = await _client.post(
      Uri.parse('$baseUrl$path'),
      headers: _buildHeaders(token),
      body: body != null ? jsonEncode(body) : null,
    );
    return _processResponse(response);
  }

  Map<String, String> _buildHeaders(String? token) {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  dynamic _processResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return null;
      
      final Map<String, dynamic> jsonResponse = jsonDecode(response.body) as Map<String, dynamic>;
      
      // Unwrap backend's SuccessResponse: { "success": true, "data": ... }
      if (jsonResponse.containsKey('success') && jsonResponse['success'] == true) {
        return jsonResponse['data'];
      }
      return jsonResponse;
    } else {
      String errorMessage = 'Unknown error';
      try {
        final Map<String, dynamic> errorJson = jsonDecode(response.body) as Map<String, dynamic>;
        // FastAPI returns validation errors as list in 'detail' or string.
        if (errorJson['detail'] is String) {
          errorMessage = errorJson['detail'];
        } else if (errorJson['detail'] is List) {
          errorMessage = (errorJson['detail'] as List).map((e) => e['msg']).join(', ');
        } else {
          errorMessage = errorJson.toString();
        }
      } catch (_) {
        if (response.body.isNotEmpty) {
           errorMessage = response.body;
        }
      }
      throw ApiException(response.statusCode, errorMessage);
    }
  }
}

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient();
});
