import 'package:amazon_cognito_identity_dart_2/cognito.dart';

import '../config/app_config.dart';

class AuthService {
  final CognitoUserPool _userPool = CognitoUserPool(
    AppConfig.cognitoUserPoolId,
    AppConfig.cognitoClientId,
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

  Future<void> signOut() async {
    await _currentUser?.signOut();
    _currentUser = null;
    _session = null;
  }
}
