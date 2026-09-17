import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/app_config.dart';

class OrderApiService {
  Future<List<Map<String, dynamic>>> getOrders({
    required String idToken,
  }) async {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}/orders');

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Bearer $idToken',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 200) {
      throw Exception(
        'Unable to load orders. HTTP ${response.statusCode}: ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);

    if (decoded is Map<String, dynamic>) {
      final orders = decoded['orders'];

      if (orders is List) {
        return orders
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList();
      }
    }

    if (decoded is List) {
      return decoded
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
    }

    return [];
  }

  Future<Map<String, dynamic>> createOrder({
    required String idToken,
    required String idempotencyKey,
    required String customerName,
    required String customerEmail,
    required List<Map<String, dynamic>> items,
  }) async {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}/orders');

    final requestBody = {
      'customer_name': customerName,
      'customer_email': customerEmail,
      'items': items,
    };

    final response = await http.post(
      uri,
      headers: {
        'Authorization': 'Bearer $idToken',
        'Content-Type': 'application/json',
        'Idempotency-Key': idempotencyKey,
      },
      body: jsonEncode(requestBody),
    );

    if (response.statusCode != 200 &&
        response.statusCode != 201 &&
        response.statusCode != 202) {
      throw Exception(
        'Unable to create order. HTTP ${response.statusCode}: ${response.body}',
      );
    }

    if (response.body.trim().isEmpty) {
      return {};
    }

    final decoded = jsonDecode(response.body);

    if (decoded is Map<String, dynamic>) {
      return decoded;
    }

    if (decoded is Map) {
      return Map<String, dynamic>.from(decoded);
    }

    return {};
  }
}
