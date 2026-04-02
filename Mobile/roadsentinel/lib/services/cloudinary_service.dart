import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;

class CloudinaryService {
  // Hardcoded for testing as requested
  CloudinaryService([dynamic _]);

  final String cloudName = 'dks1edqey';
  final String apiKey = '326677388198311';
  final String apiSecret = 'sfp-8J3NqwkijI7m1JD54Sq5GzU';

  bool get enabled => true;

  Future<String?> upload(Uint8List bytes) async {
    final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    final params = 'timestamp=$timestamp$apiSecret';
    final signature = sha1.convert(utf8.encode(params)).toString();

    final url = Uri.parse('https://api.cloudinary.com/v1_1/$cloudName/image/upload');

    try {
      final request = http.MultipartRequest('POST', url)
        ..fields['timestamp'] = timestamp.toString()
        ..fields['api_key'] = apiKey
        ..fields['signature'] = signature
        ..files.add(http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: 'detection_$timestamp.jpg',
        ));

      final response = await request.send();
      final respStr = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        final json = jsonDecode(respStr);
        final secureUrl = json['secure_url'] as String?;
        print('Cloudinary Upload Success: $secureUrl');
        return secureUrl;
      } else {
        print('Cloudinary Upload Failed (${response.statusCode}): $respStr');
      }
    } catch (e) {
      print('Cloudinary Upload Error: $e');
    }
    return null;
  }

  Future<String?> uploadImage({
    required File file,
    String? publicId,
    Map<String, String>? context,
  }) async {
    return _uploadFile(file, 'image', publicId, context);
  }

  Future<String?> uploadVideo({
    required File file,
    String? publicId,
    Map<String, String>? context,
  }) async {
    return _uploadFile(file, 'video', publicId, context);
  }

  Future<String?> _uploadFile(
    File file,
    String resourceType,
    String? publicId,
    Map<String, String>? context,
  ) async {
    final timestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;

    // Prepare signature parameters (Cloudinary requires them to be sorted alphabetically)
    final Map<String, String> signParams = {
      'timestamp': timestamp.toString(),
    };
    if (publicId != null) signParams['public_id'] = publicId;

    // Sort and join
    final sortedKeys = signParams.keys.toList()..sort();
    final signStr = sortedKeys.map((k) => '$k=${signParams[k]}').join('&');
    final signature = sha1.convert(utf8.encode('$signStr$apiSecret')).toString();

    final url = Uri.parse('https://api.cloudinary.com/v1_1/$cloudName/$resourceType/upload');

    try {
      final request = http.MultipartRequest('POST', url)
        ..fields['timestamp'] = timestamp.toString()
        ..fields['api_key'] = apiKey
        ..fields['signature'] = signature;

      if (publicId != null) request.fields['public_id'] = publicId;

      request.files.add(await http.MultipartFile.fromPath('file', file.path));

      final response = await request.send();
      final respStr = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        final json = jsonDecode(respStr);
        return json['secure_url'] as String?;
      } else {
        print('Cloudinary $resourceType Upload Failed (${response.statusCode}): $respStr');
      }
    } catch (e) {
      print('Cloudinary $resourceType Upload Error: $e');
    }
    return null;
  }
}
