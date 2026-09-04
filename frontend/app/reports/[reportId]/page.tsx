"use client";


import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Card, ErrorState, LoadingState } from "@/components/ui";
import { ReportView } from "@/components/ReportView";
import { useApiData } from "@/hooks/useApi";
import type { ReportDetail } from "@/types";

export default function ReportPage({ params }: { params: { reportId: string } }) {
  const reportId = params.reportId;
  const { data, error, loading, refresh } = useApiData<ReportDetail>(`/api/reports/${reportId}`);

  if (loading) return <LoadingState label="Loading report…" />;
  if (error) return <ErrorState message={error} retry={refresh} />;
  if (!data) return null;

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <div className="no-print mb-4">
        <Link href={`/companies/${data.company_id}/reports`}
              className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-navy-700">
          <ArrowLeft size={14} /> Back to reports
        </Link>
      </div>
      {data.content && Object.keys(data.content).length > 0 ? (
        <ReportView report={data} content={data.content} />
      ) : (
        <Card className="p-8 text-center text-sm text-slate-500">Report content unavailable.</Card>
      )}
    </main>
  );
}
