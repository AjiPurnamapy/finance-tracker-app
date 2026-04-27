class TokenResponse {
  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresIn;

  const TokenResponse({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.expiresIn,
  });

  factory TokenResponse.fromJson(Map<String, dynamic> json) {
    return switch (json) {
      {
        'access_token': String accessToken,
        'refresh_token': String refreshToken,
        'token_type': String tokenType,
        'expires_in': int expiresIn,
      } =>
        TokenResponse(
          accessToken: accessToken,
          refreshToken: refreshToken,
          tokenType: tokenType,
          expiresIn: expiresIn,
        ),
      _ => throw const FormatException('Failed to load TokenResponse from JSON.'),
    };
  }
}
