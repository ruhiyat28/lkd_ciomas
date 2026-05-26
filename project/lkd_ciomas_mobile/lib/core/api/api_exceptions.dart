class ApiException implements Exception {
  final String message;
  final int? statusCode;

  ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class UnauthorizedException extends ApiException {
  UnauthorizedException() : super('Sesi habis, silakan login ulang', statusCode: 401);
}

class NotFoundException extends ApiException {
  NotFoundException(String msg) : super(msg, statusCode: 404);
}

class ValidationException extends ApiException {
  ValidationException(String msg) : super(msg, statusCode: 400);
}
