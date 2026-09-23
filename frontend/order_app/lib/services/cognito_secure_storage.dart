import 'package:amazon_cognito_identity_dart_2/cognito.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class CognitoSecureStorage extends CognitoStorage {
  CognitoSecureStorage({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  @override
  Future<String?> getItem(String key) {
    return _storage.read(key: key);
  }

  @override
  Future<void> setItem(String key, dynamic value) {
    return _storage.write(key: key, value: value?.toString());
  }

  @override
  Future<void> removeItem(String key) {
    return _storage.delete(key: key);
  }

  @override
  Future<void> clear() {
    return _storage.deleteAll();
  }
}
