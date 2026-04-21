"""
Custom exception hierarchy for the application.
All business errors should raise these exceptions.
The global exception handler in middleware.py will convert them to HTTP responses.

Design: Every subclass accepts optional `code` and `message` overrides
so callers can provide context-specific messages without creating new classes.
"""


class AppException(Exception):
    """
    Base exception for all application errors.
    Carries HTTP status code, error code, and human-readable message.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


# ------------------------------------------------------------------ #
# 400 Bad Request
# ------------------------------------------------------------------ #

class BadRequestException(AppException):
    def __init__(
        self,
        message: str = "Permintaan tidak valid.",
        code: str = "BAD_REQUEST",
        details: dict | None = None,
    ) -> None:
        super().__init__(400, code, message, details)


class InsufficientBalanceException(AppException):
    def __init__(self, currency: str = "IDR") -> None:
        super().__init__(
            400,
            "INSUFFICIENT_BALANCE",
            f"Saldo {currency} tidak mencukupi untuk transaksi ini.",
        )


class SeatLimitException(AppException):
    def __init__(self) -> None:
        super().__init__(
            400,
            "SEAT_LIMIT_REACHED",
            "Family sudah mencapai batas anggota maksimum. "
            "Upgrade ke Pro untuk menambahkan lebih banyak anggota.",
        )


class InvalidStateTransitionException(AppException):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            400,
            "INVALID_STATE_TRANSITION",
            f"Tidak dapat mengubah status dari '{current}' ke '{target}'.",
        )


class InvitationExpiredException(AppException):
    def __init__(self) -> None:
        super().__init__(
            410,
            "INVITATION_EXPIRED",
            "Kode undangan sudah kadaluarsa. Minta parent untuk membuat kode baru.",
        )


class InvitationAlreadyUsedException(AppException):
    def __init__(self) -> None:
        super().__init__(
            409,
            "INVITATION_ALREADY_USED",
            "Kode undangan sudah digunakan.",
        )


class InvitationCancelledException(AppException):
    def __init__(self) -> None:
        super().__init__(
            410,
            "INVITATION_CANCELLED",
            "Kode undangan sudah dibatalkan. Minta parent untuk membuat kode baru.",
        )


class AlreadyMemberException(AppException):
    def __init__(self) -> None:
        super().__init__(
            409,
            "ALREADY_MEMBER",
            "Akun ini sudah tergabung dalam sebuah family.",
        )


class MinimumExchangeException(AppException):
    def __init__(self, minimum: int) -> None:
        super().__init__(
            400,
            "MINIMUM_EXCHANGE_NOT_MET",
            f"Minimal penukaran PTS adalah {minimum} PTS.",
        )


# ------------------------------------------------------------------ #
# 401 Unauthorized
# ------------------------------------------------------------------ #

class UnauthorizedException(AppException):
    def __init__(
        self,
        message: str = "Autentikasi diperlukan.",
        code: str = "UNAUTHORIZED",
        details: dict | None = None,
    ) -> None:
        super().__init__(401, code, message, details)


class InvalidCredentialsException(AppException):
    def __init__(self) -> None:
        # Generic message — do NOT reveal whether email exists or password is wrong
        super().__init__(401, "INVALID_CREDENTIALS", "Email atau password salah.")


class TokenExpiredException(AppException):
    def __init__(self) -> None:
        super().__init__(401, "TOKEN_EXPIRED", "Token sudah kadaluarsa. Silakan login ulang.")


class InvalidTokenException(AppException):
    def __init__(self) -> None:
        super().__init__(401, "INVALID_TOKEN", "Token tidak valid.")


# ------------------------------------------------------------------ #
# 403 Forbidden
# ------------------------------------------------------------------ #

class ForbiddenException(AppException):
    def __init__(
        self,
        message: str = "Anda tidak memiliki akses ke resource ini.",
        code: str = "FORBIDDEN",
        details: dict | None = None,
    ) -> None:
        super().__init__(403, code, message, details)


class InactiveAccountException(AppException):
    def __init__(self) -> None:
        super().__init__(403, "ACCOUNT_INACTIVE", "Akun ini telah dinonaktifkan.")


# ------------------------------------------------------------------ #
# 404 Not Found
# ------------------------------------------------------------------ #

class NotFoundException(AppException):
    def __init__(
        self,
        resource: str = "Resource",
        code: str = "NOT_FOUND",
    ) -> None:
        super().__init__(404, code, f"{resource} tidak ditemukan.")


# ------------------------------------------------------------------ #
# 409 Conflict
# ------------------------------------------------------------------ #

class ConflictException(AppException):
    def __init__(
        self,
        message: str = "Konflik data.",
        code: str = "CONFLICT",
        details: dict | None = None,
    ) -> None:
        super().__init__(409, code, message, details)


class EmailAlreadyExistsException(AppException):
    def __init__(self) -> None:
        super().__init__(409, "EMAIL_ALREADY_EXISTS", "Email ini sudah terdaftar.")


class FamilyAlreadyExistsException(AppException):
    def __init__(self) -> None:
        super().__init__(409, "FAMILY_EXISTS", "Anda sudah memiliki family.")
