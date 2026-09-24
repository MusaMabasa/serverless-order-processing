import 'package:flutter/material.dart';

import 'services/auth_service.dart';
import 'services/order_api_service.dart';

class OrderDetailsScreen extends StatefulWidget {
  const OrderDetailsScreen({
    super.key,
    required this.authService,
    required this.orderId,
  });

  final AuthService authService;
  final String orderId;

  @override
  State<OrderDetailsScreen> createState() => _OrderDetailsScreenState();
}

class _OrderDetailsScreenState extends State<OrderDetailsScreen> {
  final OrderApiService _apiService = OrderApiService();

  Map<String, dynamic>? _order;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadOrder();
  }

  Future<void> _loadOrder() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final token = await widget.authService.getValidIdToken();

      final order = await _apiService.getOrder(
        idToken: token,
        orderId: widget.orderId,
      );

      if (!mounted) return;

      setState(() {
        _order = order;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;

      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  String _text(dynamic value) {
    if (value == null || value.toString().trim().isEmpty) {
      return '-';
    }

    return value.toString();
  }

  String _southAfricanTime(dynamic value) {
    if (value == null || value.toString().trim().isEmpty) return '-';

    final parsed = DateTime.tryParse(value.toString());
    if (parsed == null) return value.toString();

    final sast = parsed.toUtc().add(const Duration(hours: 2));

    String twoDigits(int number) => number.toString().padLeft(2, '0');

    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];

    return '${sast.day} ${months[sast.month - 1]} ${sast.year}, '
        '${twoDigits(sast.hour)}:${twoDigits(sast.minute)}:'
        '${twoDigits(sast.second)} SAST';
  }

  String _money(dynamic value) {
    if (value == null) return '-';

    final amount = num.tryParse(value.toString());

    if (amount == null) {
      return value.toString();
    }

    return 'R${amount.toStringAsFixed(2)}';
  }

  Widget _statusChip(dynamic value) {
    final status = _text(value).toUpperCase();

    return Chip(
      avatar: const Icon(Icons.info_outline, size: 18),
      label: Text(status),
    );
  }

  Widget _detailRow({required String label, required String value}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          Expanded(child: SelectableText(value)),
        ],
      ),
    );
  }

  Widget _buildItem(Map<String, dynamic> item) {
    final name = _text(item['product'] ?? item['name']);
    final quantity = _text(item['quantity']);
    final price = _money(item['price']);

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            const Icon(Icons.inventory_2_outlined),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 4),
                  Text('Quantity: $quantity'),
                ],
              ),
            ),
            Text(price, style: const TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  Widget _buildOrderDetails() {
    final order = _order!;

    final rawItems = order['items'];
    final items = rawItems is List
        ? rawItems
              .whereType<Map>()
              .map((item) => Map<String, dynamic>.from(item))
              .toList()
        : <Map<String, dynamic>>[];

    return RefreshIndicator(
      onRefresh: _loadOrder,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          _text(order['order_id']),
                          style: Theme.of(context).textTheme.headlineSmall
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                      ),
                      _statusChip(order['status']),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Divider(),
                  _detailRow(
                    label: 'Customer',
                    value: _text(order['customer_name']),
                  ),
                  _detailRow(
                    label: 'Email',
                    value: _text(order['customer_email']),
                  ),
                  _detailRow(label: 'Total', value: _money(order['total'])),
                  _detailRow(
                    label: 'Created',
                    value: _southAfricanTime(order['created_at']),
                  ),
                  _detailRow(
                    label: 'Processed',
                    value: _southAfricanTime(order['processed_at']),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          Text(
            'Order Items',
            style: Theme.of(context).textTheme.titleLarge
                ?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          if (items.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(20),
                child: Text('No order items found.'),
              ),
            )
          else
            ...items.map(_buildItem),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Order Details'),
        actions: [
          IconButton(
            tooltip: 'Refresh order',
            onPressed: _loading ? null : _loadOrder,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline, size: 56),
                    const SizedBox(height: 16),
                    const Text(
                      'Unable to load order',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(_error!, textAlign: TextAlign.center),
                    const SizedBox(height: 20),
                    FilledButton.icon(
                      onPressed: _loadOrder,
                      icon: const Icon(Icons.refresh),
                      label: const Text('Try Again'),
                    ),
                  ],
                ),
              ),
            )
          : _buildOrderDetails(),
    );
  }
}
