import 'dart:math';

import 'package:flutter/material.dart';

import 'services/auth_service.dart';
import 'services/order_api_service.dart';

class CreateOrderScreen extends StatefulWidget {
  final AuthService authService;

  const CreateOrderScreen({super.key, required this.authService});

  @override
  State<CreateOrderScreen> createState() => _CreateOrderScreenState();
}

class _CreateOrderScreenState extends State<CreateOrderScreen> {
  final _formKey = GlobalKey<FormState>();
  final _apiService = OrderApiService();

  final _customerNameController = TextEditingController();
  final _customerEmailController = TextEditingController();
  final _productController = TextEditingController();
  final _quantityController = TextEditingController(text: '1');
  final _priceController = TextEditingController();

  bool _submitting = false;
  String? _idempotencyKey;

  String _generateIdempotencyKey() {
    final timestamp = DateTime.now().microsecondsSinceEpoch.toRadixString(36);

    final random = Random.secure().nextInt(0x7fffffff).toRadixString(36);

    return '$timestamp-$random';
  }

  void _markOrderChanged() {
    _idempotencyKey = null;
  }

  double get _total {
    final quantity = int.tryParse(_quantityController.text) ?? 0;
    final price = double.tryParse(_priceController.text) ?? 0;

    return quantity * price;
  }

  Future<void> _submitOrder() async {
    if (_submitting) {
      return;
    }

    if (!_formKey.currentState!.validate()) {
      return;
    }

    final token = widget.authService.idToken;

    if (token == null || token.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Authentication token is unavailable.')),
      );
      return;
    }

    final quantity = int.parse(_quantityController.text);
    final price = double.parse(_priceController.text);

    final idempotencyKey = _idempotencyKey ??= _generateIdempotencyKey();

    setState(() {
      _submitting = true;
    });

    try {
      final result = await _apiService.createOrder(
        idToken: token,
        idempotencyKey: idempotencyKey,
        customerName: _customerNameController.text.trim(),
        customerEmail: _customerEmailController.text.trim(),
        items: [
          {
            'product': _productController.text.trim(),
            'quantity': quantity,
            'price': price,
          },
        ],
      );

      if (!mounted) return;

      final orderId = result['order_id']?.toString() ?? 'New order';

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Order submitted successfully: $orderId')),
      );

      _idempotencyKey = null;

      Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Unable to create order: ${error.toString()}')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _customerNameController.dispose();
    _customerEmailController.dispose();
    _productController.dispose();
    _quantityController.dispose();
    _priceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create Order')),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 700),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'New Order',
                          style: TextStyle(
                            fontSize: 26,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Submit a new order to the AWS serverless backend.',
                          style: TextStyle(
                            color: Theme.of(context)
                                .colorScheme
                                .onSurfaceVariant,
                          ),
                        ),
                        const SizedBox(height: 28),

                        TextFormField(
                          controller: _customerNameController,
                          decoration: const InputDecoration(
                            labelText: 'Customer Name',
                            prefixIcon: Icon(Icons.person_outline),
                            border: OutlineInputBorder(),
                          ),
                          onChanged: (_) {
                            _markOrderChanged();
                          },
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return 'Customer name is required.';
                            }

                            return null;
                          },
                        ),

                        const SizedBox(height: 16),

                        TextFormField(
                          controller: _customerEmailController,
                          keyboardType: TextInputType.emailAddress,
                          decoration: const InputDecoration(
                            labelText: 'Customer Email',
                            prefixIcon: Icon(Icons.email_outlined),
                            border: OutlineInputBorder(),
                          ),
                          onChanged: (_) {
                            _markOrderChanged();
                          },
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return 'Customer email is required.';
                            }

                            if (!value.contains('@')) {
                              return 'Enter a valid email address.';
                            }

                            return null;
                          },
                        ),

                        const SizedBox(height: 28),

                        const Text(
                          'Order Item',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),

                        const SizedBox(height: 16),

                        TextFormField(
                          controller: _productController,
                          decoration: const InputDecoration(
                            labelText: 'Product',
                            prefixIcon: Icon(Icons.inventory_2_outlined),
                            border: OutlineInputBorder(),
                          ),
                          onChanged: (_) {
                            _markOrderChanged();
                          },
                          validator: (value) {
                            if (value == null || value.trim().isEmpty) {
                              return 'Product is required.';
                            }

                            return null;
                          },
                        ),

                        const SizedBox(height: 16),

                        LayoutBuilder(
                          builder: (context, constraints) {
                            final narrow = constraints.maxWidth < 500;

                            final quantityField = TextFormField(
                              controller: _quantityController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: 'Quantity',
                                prefixIcon: Icon(Icons.numbers_outlined),
                                border: OutlineInputBorder(),
                              ),
                              onChanged: (_) {
                                _markOrderChanged();
                                setState(() {});
                              },
                              validator: (value) {
                                final quantity = int.tryParse(value ?? '');

                                if (quantity == null || quantity < 1) {
                                  return 'Minimum quantity is 1.';
                                }

                                return null;
                              },
                            );

                            final priceField = TextFormField(
                              controller: _priceController,
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                    decimal: true,
                                  ),
                              decoration: const InputDecoration(
                                labelText: 'Price',
                                prefixText: 'R ',
                                prefixIcon: Icon(Icons.payments_outlined),
                                border: OutlineInputBorder(),
                              ),
                              onChanged: (_) {
                                _markOrderChanged();
                                setState(() {});
                              },
                              validator: (value) {
                                final price = double.tryParse(value ?? '');

                                if (price == null || price < 0) {
                                  return 'Enter a valid price.';
                                }

                                return null;
                              },
                            );

                            if (narrow) {
                              return Column(
                                children: [
                                  quantityField,
                                  const SizedBox(height: 16),
                                  priceField,
                                ],
                              );
                            }

                            return Row(
                              children: [
                                Expanded(child: quantityField),
                                const SizedBox(width: 16),
                                Expanded(child: priceField),
                              ],
                            );
                          },
                        ),
                        const SizedBox(height: 24),

                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(18),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            color: Theme.of(context)
                                .colorScheme
                                .surfaceContainerHighest,
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text(
                                'Order Total',
                                style: TextStyle(fontWeight: FontWeight.w500),
                              ),
                              Text(
                                'R ${_total.toStringAsFixed(2)}',
                                style: const TextStyle(
                                  fontSize: 22,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 28),

                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            onPressed: _submitting ? null : _submitOrder,
                            icon: _submitting
                                ? const SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Icon(Icons.send),
                            label: Text(
                              _submitting ? 'Submitting...' : 'Submit Order',
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
