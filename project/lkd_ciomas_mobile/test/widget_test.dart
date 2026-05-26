import 'package:flutter_test/flutter_test.dart';
import 'package:lkd_ciomas_mobile/app.dart';

void main() {
  testWidgets('App loads', (WidgetTester tester) async {
    await tester.pumpWidget(const LkdApp());
    expect(find.text('LKD CIOMAS'), findsNothing);
  });
}
