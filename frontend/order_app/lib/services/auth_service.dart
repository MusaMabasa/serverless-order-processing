import 'package:amazon_cognito_identity_dart_2/cognito.dart';

import '../config/app_config.dart';
import 'cognito_secure_storage.dart';

class AuthService {
  final CognitoUserPool _userPool = CognitoUserPool(
    AppConfig.cognitoUserPoolId,
    AppConfig.cognitoClientId,
    storage: CognitoSecureStorage(),
  );

  CognitoUserSession? _session;
  CognitoUser? _currentUser;

  Future<CognitoUserSession> signIn({
    required String email,
    required String password,
  }) async {
    final user = CognitoUser(email, _userPool);

    final authDetails = AuthenticationDetails(
      username: email,
      password: password,
    );

    final session = await user.authenticateUser(authDetails);

    if (session == null || !session.isValid()) {
      throw Exception('Authentication failed.');
    }

    _currentUser = user;
    _session = session;

    return session;
  }

  String? get idToken => _session?.idToken.jwtToken;

  bool get isSignedIn => _session?.isValid() ?? false;

  Future<String> getValidIdToken() async {
    if (_session?.isValid() ?? false) {
      final token = _session?.idToken.jwtToken;

      if (token != null && token.isNotEmpty) {
        return token;
      }
    }

    final user = _currentUser ?? await _userPool.getCurrentUser();

    if (user == null) {
      throw Exception('No authenticated user. Please sign in again.');
    }

    final session = await user.getSession();

    if (session == null || !session.isValid()) {
      throw Exception('Unable to restore authentication session.');
    }

    final token = session.idToken.jwtToken;

    if (token == null || token.isEmpty) {
      throw Exception('Authentication session does not contain an ID token.');
    }

    _currentUser = user;
    _session = session;

    return token;
  }

  Future<void> signOut() async {
    final user = _currentUser ?? await _userPool.getCurrentUser();

    await user?.signOut();

    _currentUser = null;
    _session = null;
  }
}
