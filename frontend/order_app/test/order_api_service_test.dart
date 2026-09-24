import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:order_app/services/order_api_service.dart';

void main() {
  test('GET orders returns the order list', () async {
    final client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, endsWith('/orders'));
      expect(request.headers['Authorization'], 'Bearer test-token');

      return http.Response(
        jsonEncode({
          'orders': [
            {'order_id': 'ORD-001'},
          ],
        }),
        200,
      );
    });

    final service = OrderApiService(client: client);
    final orders = await service.getOrders(idToken: 'test-token');

    expect(orders.length, 1);
    expect(orders.first['order_id'], 'ORD-001');
    client.close();
  });

  test('GET orders reports API errors', () async {
    final client = MockClient((request) async {
      return http.Response('Unauthorized', 401);
    });

    final service = OrderApiService(client: client);

    await expectLater(
      service.getOrders(idToken: 'invalid-token'),
      throwsA(isA<Exception>()),
    );

    client.close();
  });

  test('GET single order returns the order', () async {
    final client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, endsWith('/orders/ORD-001'));
      expect(request.headers['Authorization'], 'Bearer test-token');

      return http.Response(
        jsonEncode({
          'order': {
            'order_id': 'ORD-001',
            'customer_name': 'Test Customer',
            'customer_email': 'test@example.com',
            'status': 'COMPLETED',
            'total': 250,
          },
        }),
        200,
      );
    });

    final service = OrderApiService(client: client);

    final order = await service.getOrder(
      idToken: 'test-token',
      orderId: 'ORD-001',
    );

    expect(order['order_id'], 'ORD-001');
    expect(order['customer_name'], 'Test Customer');
    expect(order['status'], 'COMPLETED');
    expect(order['total'], 250);

    client.close();
  });

  test('GET single order reports API errors', () async {
    final client = MockClient((request) async {
      expect(request.method, 'GET');
      expect(request.url.path, endsWith('/orders/ORD-NOTFOUND'));

      return http.Response(
        jsonEncode({'message': 'Order not found', 'order_id': 'ORD-NOTFOUND'}),
        404,
      );
    });

    final service = OrderApiService(client: client);

    await expectLater(
      service.getOrder(idToken: 'test-token', orderId: 'ORD-NOTFOUND'),
      throwsA(
        isA<Exception>().having(
          (error) => error.toString(),
          'message',
          contains('HTTP 404'),
        ),
      ),
    );

    client.close();
  });

  test('POST orders sends idempotency key and correct body', () async {
    final client = MockClient((request) async {
      expect(request.method, 'POST');
      expect(request.url.path, endsWith('/orders'));
      expect(request.headers['Authorization'], 'Bearer test-token');
      expect(request.headers['Idempotency-Key'], 'unique-test-key');

      final body = jsonDecode(request.body) as Map<String, dynamic>;
      expect(body['customer_name'], 'Test Customer');
      expect(body['customer_email'], 'test@example.com');
      expect(body['items'], [
        {'name': 'Laptop', 'quantity': 1, 'price': 100},
      ]);

      return http.Response(
        jsonEncode({'order_id': 'ORD-002', 'status': 'QUEUED'}),
        202,
      );
    });

    final clientService = OrderApiService(client: client);

    final result = await clientService.createOrder(
      idToken: 'test-token',
      idempotencyKey: 'unique-test-key',
      customerName: 'Test Customer',
      customerEmail: 'test@example.com',
      items: [
        {'name': 'Laptop', 'quantity': 1, 'price': 100},
      ],
    );

    expect(result['order_id'], 'ORD-002');
    expect(result['status'], 'QUEUED');
    client.close();
  });

  test('POST orders reports API errors', () async {
    final client = MockClient((request) async {
      return http.Response('Service unavailable', 503);
    });

    final service = OrderApiService(client: client);

    await expectLater(
      service.createOrder(
        idToken: 'test-token',
        idempotencyKey: 'error-test-key',
        customerName: 'Test Customer',
        customerEmail: 'test@example.com',
        items: [
          {'name': 'Laptop', 'quantity': 1, 'price': 100},
        ],
      ),
      throwsA(
        isA<Exception>().having(
          (error) => error.toString(),
          'message',
          contains('HTTP 503'),
        ),
      ),
    );

    client.close();
  });
}
