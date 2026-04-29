from __future__ import annotations

from domain.alert.value_objects import AlertType as DomainAlertType
from infrastructure.db.models.alert.tables import AlertType as InfraAlertType


class TestAlertTypeSync:
    def test_alert_type_members_match(self) -> None:
        domain_members = {member.value for member in DomainAlertType}
        infra_members = {member.value for member in InfraAlertType}

        assert domain_members == infra_members, (
            f"AlertType enums are out of sync.\n"
            f"Domain members: {sorted(domain_members)}\n"
            f"Infrastructure members: {sorted(infra_members)}\n"
            "Ensure both AlertType enums have the same members."
        )

    def test_alert_type_names_match(self) -> None:
        domain_names = {member.name for member in DomainAlertType}
        infra_names = {member.name for member in InfraAlertType}

        assert domain_names == infra_names, (
            f"AlertType enum names are out of sync.\n"
            f"Domain names: {sorted(domain_names)}\n"
            f"Infrastructure names: {sorted(infra_names)}\n"
            "Ensure both AlertType enums have the same names."
        )

    def test_alert_type_values_match(self) -> None:
        domain_values = {member.value for member in DomainAlertType}
        infra_values = {member.value for member in InfraAlertType}

        assert domain_values == infra_values, (
            f"AlertType enum values are out of sync.\n"
            f"Domain values: {sorted(domain_values)}\n"
            f"Infrastructure values: {sorted(infra_values)}\n"
            "Ensure both AlertType enums have the same values."
        )
