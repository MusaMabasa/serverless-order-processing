import 'package:flutter_test/flutter_test.dart';
import 'package:order_app/main.dart';

void main() {
  testWidgets('Login screen renders correctly', (WidgetTester tester) async {
    await tester.pumpWidget(const OrderApp());

    expect(find.text('Serverless Order Processing'), findsOneWidget);
    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
  });
}
