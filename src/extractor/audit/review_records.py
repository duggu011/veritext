from __future__ import annotations

from extractor.audit.base import SQLiteAuditStore
from extractor.audit.models import CandidateRejection
from extractor.contracts import CriticReport, DataPoint, LensCandidate, VerifierReport


class ReviewAuditRecords(SQLiteAuditStore):
    async def record_lens_candidate(self, candidate: LensCandidate) -> None:
        await self._insert_payload(
            "lens_candidates",
            {
                "candidate_id": candidate.candidate_id,
                "run_id": candidate.run_id,
                "doc_id": candidate.doc_id,
                "chunk_id": candidate.chunk_id,
                "category": candidate.category,
                "field_name": candidate.field_name,
                "payload_json": candidate.model_dump_json(),
            },
        )

    async def get_lens_candidate(self, candidate_id: str) -> LensCandidate | None:
        return await self._fetch_payload(
            "lens_candidates",
            "candidate_id",
            candidate_id,
            LensCandidate,
        )

    async def list_lens_candidates(self, run_id: str) -> tuple[LensCandidate, ...]:
        return await self._list_payloads(
            "lens_candidates",
            LensCandidate,
            "run_id = ?",
            (run_id,),
            "candidate_id ASC",
        )

    async def record_critic_report(self, report: CriticReport) -> None:
        await self._insert_payload(
            "critic_reports",
            {
                "report_id": report.report_id,
                "run_id": report.run_id,
                "candidate_id": report.candidate_id,
                "accepted": int(report.accepted),
                "payload_json": report.model_dump_json(),
            },
        )

    async def get_critic_report(self, report_id: str) -> CriticReport | None:
        return await self._fetch_payload("critic_reports", "report_id", report_id, CriticReport)

    async def list_critic_reports(self, candidate_id: str) -> tuple[CriticReport, ...]:
        return await self._list_payloads(
            "critic_reports",
            CriticReport,
            "candidate_id = ?",
            (candidate_id,),
            "report_id ASC",
        )

    async def list_critic_reports_for_run(self, run_id: str) -> tuple[CriticReport, ...]:
        return await self._list_payloads(
            "critic_reports",
            CriticReport,
            "run_id = ?",
            (run_id,),
            "candidate_id ASC, report_id ASC",
        )

    async def record_verifier_report(self, report: VerifierReport) -> None:
        await self._insert_payload(
            "verifier_reports",
            {
                "report_id": report.report_id,
                "run_id": report.run_id,
                "candidate_id": report.candidate_id,
                "accepted": int(report.accepted),
                "payload_json": report.model_dump_json(),
            },
        )

    async def get_verifier_report(self, report_id: str) -> VerifierReport | None:
        return await self._fetch_payload(
            "verifier_reports",
            "report_id",
            report_id,
            VerifierReport,
        )

    async def list_verifier_reports(self, candidate_id: str) -> tuple[VerifierReport, ...]:
        return await self._list_payloads(
            "verifier_reports",
            VerifierReport,
            "candidate_id = ?",
            (candidate_id,),
            "report_id ASC",
        )

    async def list_verifier_reports_for_run(self, run_id: str) -> tuple[VerifierReport, ...]:
        return await self._list_payloads(
            "verifier_reports",
            VerifierReport,
            "run_id = ?",
            (run_id,),
            "candidate_id ASC, report_id ASC",
        )

    async def record_data_point(self, data_point: DataPoint) -> None:
        await self._insert_payload(
            "data_points",
            {
                "data_point_id": data_point.data_point_id,
                "run_id": data_point.run_id,
                "doc_id": data_point.doc_id,
                "category": data_point.category,
                "field_name": data_point.field_name,
                "payload_json": data_point.model_dump_json(),
            },
        )

    async def get_data_point(self, data_point_id: str) -> DataPoint | None:
        return await self._fetch_payload("data_points", "data_point_id", data_point_id, DataPoint)

    async def list_data_points(self, run_id: str) -> tuple[DataPoint, ...]:
        return await self._list_payloads(
            "data_points",
            DataPoint,
            "run_id = ?",
            (run_id,),
            "data_point_id ASC",
        )

    async def record_candidate_rejection(self, rejection: CandidateRejection) -> None:
        values = rejection.model_dump(mode="json")
        await self._insert_payload(
            "candidate_rejections",
            {
                "rejection_id": rejection.rejection_id,
                "run_id": rejection.run_id,
                "candidate_id": rejection.candidate_id,
                "stage": rejection.stage,
                "created_at": values["created_at"],
                "payload_json": rejection.model_dump_json(),
            },
        )

    async def get_candidate_rejection(self, rejection_id: str) -> CandidateRejection | None:
        return await self._fetch_payload(
            "candidate_rejections",
            "rejection_id",
            rejection_id,
            CandidateRejection,
        )

    async def list_candidate_rejections(self, candidate_id: str) -> tuple[CandidateRejection, ...]:
        return await self._list_payloads(
            "candidate_rejections",
            CandidateRejection,
            "candidate_id = ?",
            (candidate_id,),
            "created_at ASC, rejection_id ASC",
        )

    async def list_candidate_rejections_for_run(
        self,
        run_id: str,
    ) -> tuple[CandidateRejection, ...]:
        return await self._list_payloads(
            "candidate_rejections",
            CandidateRejection,
            "run_id = ?",
            (run_id,),
            "stage ASC, candidate_id ASC, created_at ASC, rejection_id ASC",
        )


__all__ = [
    "ReviewAuditRecords",
]
