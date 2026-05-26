class ApiResponse<T> {
  final bool success;
  final T? data;
  final String? message;
  final Pagination? pagination;

  ApiResponse({
    required this.success,
    this.data,
    this.message,
    this.pagination,
  });

  factory ApiResponse.fromJson(
    Map<String, dynamic> json,
    T Function(dynamic)? fromJsonT,
  ) {
    return ApiResponse(
      success: json['success'] as bool? ?? false,
      data: json['data'] != null ? fromJsonT?.call(json['data']) : null,
      message: json['message'] as String?,
      pagination: json['pagination'] != null
          ? Pagination.fromJson(json['pagination'])
          : null,
    );
  }
}

class Pagination {
  final int page;
  final int perPage;
  final int total;
  final int pages;

  Pagination({
    required this.page,
    required this.perPage,
    required this.total,
    required this.pages,
  });

  factory Pagination.fromJson(Map<String, dynamic> json) {
    return Pagination(
      page: json['page'] as int? ?? 1,
      perPage: json['per_page'] as int? ?? 20,
      total: json['total'] as int? ?? 0,
      pages: json['pages'] as int? ?? 0,
    );
  }
}
