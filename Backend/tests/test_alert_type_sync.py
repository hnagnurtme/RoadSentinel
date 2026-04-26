"""
tests/test_alert_type_sync.py
------------------------------
Test to ensure AlertType enums in domain and infrastructure stay synchronized.

This test prevents the silent runtime error that occurs when a new alert type
is added to one enum but not the other, which would break the mapping in
alert_repository_impl.py.
"""
from __future__ import annotations

import pytest

from domain.alert.value_objects import AlertType as DomainAlertType
from infrastructure.db.models.alert.tables import AlertType as InfraAlertType


class TestAlertTypeSync:
    """Test that AlertType enums stay synchronized between domain and infrastructure."""
    
    def test_alert_type_members_match(self) -> None:
        """Domain and infrastructure AlertType enums should have identical members."""
        domain_members = {member.value for member in DomainAlertType}
        infra_members = {member.value for member in InfraAlertType}
        
        assert domain_members == infra_members, (
            f"AlertType enums are out of sync.\n"
            f"Domain members: {sorted(domain_members)}\n"
            f"Infrastructure members: {sorted(infra_members)}\n"
            "Ensure both AlertType enums have the same members."
        )
    
    def test_alert_type_names_match(self) -> None:
        """Domain and infrastructure AlertType enums should have identical names."""
        domain_names = {member.name for member in DomainAlertType}
        infra_names = {member.name for member in InfraAlertType}
        
        assert domain_names == infra_names, (
            f"AlertType enum names are out of sync.\n"
            f"Domain names: {sorted(domain_names)}\n"
            f"Infrastructure names: {sorted(infra_names)}\n"
            "Ensure both AlertType enums have the same names."
        )
    
    def test_alert_type_values_match(self) -> None:
        """Domain and infrastructure AlertType enums should have identical values."""
        domain_values = {member.value for member in DomainAlertType}
        infra_values = {member.value for member in InfraAlertType}
        
        assert domain_values == infra_values, (
            f"AlertType enum values are out of sync.\n"
            f"Domain values: {sorted(domain_values)}\n"
            f"Infrastructure values: {sorted(infra_values)}\n"
            "Ensure both AlertType enums have the same values."
        )
