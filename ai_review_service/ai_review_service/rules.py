"""Deterministic checks that run before any optional generative review."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from .contracts import (
    ExpenseLineSnapshot,
    ExpenseReviewRequested,
    FindingSeverity,
    FindingType,
    HistoricalCategoryBaseline,
    PolicyRuleSnapshot,
    ReviewFinding,
    RuleEvaluation,
)


class RuleEvaluator:
    """Evaluate immutable policy snapshots and aggregate anomaly signals.

    This class is intentionally pure: it receives a data contract and produces
    a result, with no core-DB query or side effect.  The core service is
    responsible for supplying the correct policy version and aggregate history.
    """

    def evaluate(self, event: ExpenseReviewRequested) -> RuleEvaluation:
        currencies = {item.currency for item in event.items}
        if len(currencies) != 1:
            raise ValueError("AI review requires a single report currency; convert amounts upstream")

        category_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        findings: list[ReviewFinding] = []
        seen_receipts: dict[str, ExpenseLineSnapshot] = {}
        seen_claims: dict[tuple[str, str | None, Decimal, object, str | None], ExpenseLineSnapshot] = {}
        known_receipts = set(event.known_receipt_digests)

        for item in event.items:
            category_totals[item.category_code] += item.amount
            matching_rules = tuple(self._matching_rules(item, event.policy.rules))
            if not matching_rules:
                findings.append(
                    self._finding(
                        finding_type=FindingType.UNCONFIGURED_CATEGORY,
                        severity=FindingSeverity.MEDIUM,
                        line_id=item.line_id,
                        category=item.category_code,
                        message="The line item's category is not covered by the submitted policy snapshot.",
                    )
                )
            else:
                for rule in matching_rules:
                    findings.extend(self._evaluate_item_against_rule(item, rule))

            findings.extend(self._detect_duplicate(item, seen_receipts, seen_claims, known_receipts))

        for rule in event.policy.rules:
            if rule.max_per_report is None:
                continue
            matching_total = sum(
                (item.amount for item in event.items if self._matches_rule(item, rule)),
                Decimal("0"),
            )
            if matching_total > rule.max_per_report:
                findings.append(
                    self._finding(
                        finding_type=FindingType.POLICY_REPORT_CAP_EXCEEDED,
                        severity=FindingSeverity.HIGH,
                        category=rule.category_code,
                        rule=rule,
                        message="The category total exceeds the policy's report-level cap.",
                        evidence={
                            "category_total": matching_total,
                            "max_per_report": rule.max_per_report,
                        },
                    )
                )

        findings.extend(self._unusual_spend_findings(category_totals, event.historical_baselines))
        risk_level = self._risk_level(findings)
        return RuleEvaluation(
            report_total=sum(category_totals.values(), Decimal("0")),
            currency=currencies.pop(),
            category_totals=dict(category_totals),
            findings=tuple(findings),
            risk_level=risk_level,
        )

    @staticmethod
    def _matches_rule(item: ExpenseLineSnapshot, rule: PolicyRuleSnapshot) -> bool:
        return item.category_code == rule.category_code and (
            rule.subcategory_code is None or item.subcategory_code == rule.subcategory_code
        )

    def _matching_rules(
        self, item: ExpenseLineSnapshot, rules: tuple[PolicyRuleSnapshot, ...]
    ) -> Iterable[PolicyRuleSnapshot]:
        return (rule for rule in rules if self._matches_rule(item, rule))

    def _evaluate_item_against_rule(
        self, item: ExpenseLineSnapshot, rule: PolicyRuleSnapshot
    ) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        if rule.max_per_item is not None and item.amount > rule.max_per_item:
            findings.append(
                self._finding(
                    finding_type=FindingType.POLICY_LIMIT_EXCEEDED,
                    severity=FindingSeverity.HIGH,
                    line_id=item.line_id,
                    category=item.category_code,
                    rule=rule,
                    message="The line item amount exceeds the policy's per-item cap.",
                    evidence={"amount": item.amount, "max_per_item": rule.max_per_item},
                )
            )
        if (
            rule.receipt_required_at_or_above is not None
            and item.amount >= rule.receipt_required_at_or_above
            and not item.receipt.attached
        ):
            findings.append(
                self._finding(
                    finding_type=FindingType.MISSING_RECEIPT,
                    severity=FindingSeverity.MEDIUM,
                    line_id=item.line_id,
                    category=item.category_code,
                    rule=rule,
                    message="A receipt is required at this amount under the submitted policy snapshot.",
                    evidence={"receipt_threshold": rule.receipt_required_at_or_above},
                )
            )
        if item.vendor_code and rule.allowed_vendor_codes and item.vendor_code not in rule.allowed_vendor_codes:
            findings.append(
                self._finding(
                    finding_type=FindingType.DISALLOWED_VENDOR,
                    severity=FindingSeverity.MEDIUM,
                    line_id=item.line_id,
                    category=item.category_code,
                    rule=rule,
                    message="The line item's vendor is not in the policy's allowed-vendor list.",
                )
            )
        if item.vendor_code and (vendor_cap := rule.vendor_caps.get(item.vendor_code)) is not None and item.amount > vendor_cap:
            findings.append(
                self._finding(
                    finding_type=FindingType.VENDOR_CAP_EXCEEDED,
                    severity=FindingSeverity.HIGH,
                    line_id=item.line_id,
                    category=item.category_code,
                    rule=rule,
                    message="The line item amount exceeds the vendor-specific policy cap.",
                    evidence={"amount": item.amount, "vendor_cap": vendor_cap},
                )
            )
        return findings

    def _detect_duplicate(
        self,
        item: ExpenseLineSnapshot,
        seen_receipts: dict[str, ExpenseLineSnapshot],
        seen_claims: dict[tuple[str, str | None, Decimal, object, str | None], ExpenseLineSnapshot],
        known_receipts: set[str],
    ) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        digest = item.receipt.digest
        if digest:
            if digest in known_receipts:
                findings.append(
                    self._finding(
                        finding_type=FindingType.POTENTIAL_DUPLICATE,
                        severity=FindingSeverity.HIGH,
                        line_id=item.line_id,
                        category=item.category_code,
                        message="The receipt digest matches a previously submitted claim.",
                        evidence={"duplicate_basis": "known_receipt_digest"},
                    )
                )
            elif digest in seen_receipts:
                findings.append(
                    self._finding(
                        finding_type=FindingType.POTENTIAL_DUPLICATE,
                        severity=FindingSeverity.HIGH,
                        line_id=item.line_id,
                        category=item.category_code,
                        message="The receipt digest is reused by another line item in this report.",
                        evidence={"duplicate_basis": "report_receipt_digest"},
                    )
                )
            else:
                seen_receipts[digest] = item

        claim_signature = (
            item.category_code,
            item.subcategory_code,
            item.amount,
            item.expense_date,
            item.vendor_code,
        )
        if claim_signature in seen_claims:
            findings.append(
                self._finding(
                    finding_type=FindingType.POTENTIAL_DUPLICATE,
                    severity=FindingSeverity.MEDIUM,
                    line_id=item.line_id,
                    category=item.category_code,
                    message="A matching category, date, vendor, and amount appears elsewhere in this report.",
                    evidence={"duplicate_basis": "matching_claim_fields"},
                )
            )
        else:
            seen_claims[claim_signature] = item
        return findings

    def _unusual_spend_findings(
        self,
        category_totals: dict[str, Decimal],
        baselines: tuple[HistoricalCategoryBaseline, ...],
    ) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        baseline_by_category = {baseline.category_code: baseline for baseline in baselines}
        for category, total in category_totals.items():
            baseline = baseline_by_category.get(category)
            if baseline is None or baseline.sample_size < 3:
                continue
            threshold = baseline.average_amount * baseline.alert_multiplier
            if total > threshold:
                findings.append(
                    self._finding(
                        finding_type=FindingType.UNUSUAL_SPEND,
                        severity=FindingSeverity.MEDIUM,
                        category=category,
                        message="The category total is materially above its aggregate historical baseline.",
                        evidence={
                            "category_total": total,
                            "historical_average": baseline.average_amount,
                            "alert_multiplier": baseline.alert_multiplier,
                        },
                    )
                )
        return findings

    @staticmethod
    def _risk_level(findings: list[ReviewFinding]) -> FindingSeverity:
        if any(finding.severity == FindingSeverity.HIGH for finding in findings):
            return FindingSeverity.HIGH
        if any(finding.severity == FindingSeverity.MEDIUM for finding in findings):
            return FindingSeverity.MEDIUM
        return FindingSeverity.LOW

    @staticmethod
    def _finding(
        *,
        finding_type: FindingType,
        severity: FindingSeverity,
        message: str,
        line_id=None,
        category: str | None = None,
        rule: PolicyRuleSnapshot | None = None,
        evidence: dict | None = None,
    ) -> ReviewFinding:
        return ReviewFinding(
            finding_type=finding_type,
            severity=severity,
            message=message,
            line_id=line_id,
            category_code=category,
            policy_rule_ref=rule.rule_ref if rule else None,
            evidence=evidence or {},
        )
