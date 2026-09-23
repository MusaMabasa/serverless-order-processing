import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:order_app/main.dart';
import 'package:order_app/services/auth_service.dart';

void main() {
  testWidgets('Login screen renders correctly', (WidgetTester tester) async {
    final authService = AuthService();

    await tester.pumpWidget(
      MaterialApp(home: LoginScreen(authService: authService)),
    );

    expect(find.text('Serverless Order Processing'), findsOneWidget);
    expect(find.text('Sign in with Amazon Cognito'), findsOneWidget);
    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
  });
}
