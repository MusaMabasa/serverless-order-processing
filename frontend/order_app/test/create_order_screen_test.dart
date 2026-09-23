import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:order_app/create_order_screen.dart';
import 'package:order_app/services/auth_service.dart';

void main() {
  testWidgets('Create Order screen renders correctly', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(home: CreateOrderScreen(authService: AuthService())),
    );

    expect(find.text('Create Order'), findsOneWidget);
    expect(find.text('Customer Name'), findsOneWidget);
    expect(find.text('Customer Email'), findsOneWidget);
    expect(find.text('Product'), findsOneWidget);
    expect(find.text('Quantity'), findsOneWidget);
    expect(find.text('Price'), findsOneWidget);
    expect(find.text('Order Total'), findsOneWidget);
    expect(find.text('Submit Order'), findsOneWidget);
  });

  testWidgets('Create Order validates required fields', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(home: CreateOrderScreen(authService: AuthService())),
    );

    await tester.ensureVisible(find.text('Submit Order'));
    await tester.tap(find.text('Submit Order'));
    await tester.pump();

    expect(find.text('Customer name is required.'), findsOneWidget);
    expect(find.text('Customer email is required.'), findsOneWidget);
    expect(find.text('Product is required.'), findsOneWidget);
    expect(find.text('Minimum quantity is 1.'), findsNothing);
    expect(find.text('Enter a valid price.'), findsOneWidget);
  });
}
