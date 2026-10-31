"""Unit tests for beacon.core.errors module.

Tests custom exception classes used throughout the Beacon framework.
"""

import pytest
from beacon.core.errors import (
    PreconditionFailed,
    MissingBeaconPermissions,
    RateLimited,
    NotBotOwner
)


class TestPreconditionFailed:
    """Test suite for PreconditionFailed base exception."""
    
    def test_initialization(self):
        """Test PreconditionFailed can be initialized with a message."""
        error = PreconditionFailed("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_inheritance(self):
        """Test PreconditionFailed inherits from AppCommandError."""
        from discord.app_commands import AppCommandError
        error = PreconditionFailed("Test")
        assert isinstance(error, AppCommandError)


class TestMissingBeaconPermissions:
    """Test suite for MissingBeaconPermissions exception."""
    
    def test_single_permission(self):
        """Test error message with a single missing permission."""
        error = MissingBeaconPermissions(["manage_messages"])
        assert "Manage Messages" in error.message
        assert error.missing_permissions == ["manage_messages"]
    
    def test_multiple_permissions(self):
        """Test error message with multiple missing permissions."""
        error = MissingBeaconPermissions(["manage_messages", "kick_members", "ban_members"])
        assert "Manage Messages" in error.message
        assert "Kick Members" in error.message
        assert "Ban Members" in error.message
        assert error.missing_permissions == ["manage_messages", "kick_members", "ban_members"]
    
    def test_permission_formatting(self):
        """Test that underscores are converted to spaces and title cased."""
        error = MissingBeaconPermissions(["moderate_members"])
        assert "Moderate Members" in error.message
        assert "moderate_members" not in error.message
    
    def test_empty_permissions_list(self):
        """Test error with empty permissions list."""
        error = MissingBeaconPermissions([])
        assert error.missing_permissions == []
        # Message should still be formatted correctly even if empty
        assert "don't have the following permissions" in error.message
    
    def test_complex_permission_names(self):
        """Test formatting of complex permission names."""
        error = MissingBeaconPermissions(["view_audit_log", "manage_guild", "use_external_emojis"])
        assert "View Audit Log" in error.message
        assert "Manage Guild" in error.message
        assert "Use External Emojis" in error.message
    
    def test_inheritance(self):
        """Test MissingBeaconPermissions inherits from PreconditionFailed."""
        error = MissingBeaconPermissions(["manage_messages"])
        assert isinstance(error, PreconditionFailed)


class TestRateLimited:
    """Test suite for RateLimited exception."""
    
    def test_initialization_with_integer(self):
        """Test RateLimited with integer retry_after value."""
        error = RateLimited(5)
        assert error.retry_after == 5
        assert "5s" in error.message
    
    def test_initialization_with_float(self):
        """Test RateLimited with float retry_after value."""
        error = RateLimited(3.7)
        assert error.retry_after == 3.7
        assert "4s" in error.message  # Should round to 4
    
    def test_rounding_behavior(self):
        """Test that retry_after is rounded in the message."""
        error1 = RateLimited(2.4)
        assert "2s" in error1.message
        
        error2 = RateLimited(2.6)
        assert "3s" in error2.message
    
    def test_zero_retry_after(self):
        """Test RateLimited with zero retry_after."""
        error = RateLimited(0)
        assert error.retry_after == 0
        assert "0s" in error.message
    
    def test_large_retry_after(self):
        """Test RateLimited with large retry_after value."""
        error = RateLimited(300)
        assert error.retry_after == 300
        assert "300s" in error.message
    
    def test_message_format(self):
        """Test the complete error message format."""
        error = RateLimited(10)
        assert "using commands too quickly" in error.message.lower()
        assert "try again" in error.message.lower()
    
    def test_inheritance(self):
        """Test RateLimited inherits from PreconditionFailed."""
        error = RateLimited(5)
        assert isinstance(error, PreconditionFailed)


class TestNotBotOwner:
    """Test suite for NotBotOwner exception."""
    
    def test_initialization(self):
        """Test NotBotOwner initializes with default message."""
        error = NotBotOwner()
        assert "restricted to the bot owner" in error.message.lower()
    
    def test_message_content(self):
        """Test that the message clearly indicates owner-only restriction."""
        error = NotBotOwner()
        assert error.message == "This command is restricted to the bot owner."
    
    def test_inheritance(self):
        """Test NotBotOwner inherits from PreconditionFailed."""
        error = NotBotOwner()
        assert isinstance(error, PreconditionFailed)
    
    def test_str_representation(self):
        """Test string representation of the error."""
        error = NotBotOwner()
        assert str(error) == "This command is restricted to the bot owner."
