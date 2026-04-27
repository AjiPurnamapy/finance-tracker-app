class User {
  final String id;
  final String email;
  final String fullName;
  final String? avatarUrl;
  final String role;
  final bool isActive;
  final bool isVerified;
  final DateTime createdAt;

  const User({
    required this.id,
    required this.email,
    required this.fullName,
    this.avatarUrl,
    required this.role,
    required this.isActive,
    required this.isVerified,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return switch (json) {
      {
        'id': String id,
        'email': String email,
        'full_name': String fullName,
        'role': String role,
        'is_active': bool isActive,
        'is_verified': bool isVerified,
        'created_at': String createdAtStr,
      } =>
        User(
          id: id,
          email: email,
          fullName: fullName,
          avatarUrl: json['avatar_url'] as String?,
          role: role,
          isActive: isActive,
          isVerified: isVerified,
          createdAt: DateTime.parse(createdAtStr),
        ),
      _ => throw const FormatException('Failed to load User from JSON.'),
    };
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      if (avatarUrl != null) 'avatar_url': avatarUrl,
      'role': role,
      'is_active': isActive,
      'is_verified': isVerified,
      'created_at': createdAt.toIso8601String(),
    };
  }
}
