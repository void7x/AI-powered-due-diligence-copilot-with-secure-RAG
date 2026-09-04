"use client";


import { EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { OpportunityCard } from "@/components/OpportunityCard";
import { useApiData } from "@/hooks/useApi";
import type { Opportunity } from "@/types";

export default function OpportunitiesPage({ params }: { params: { id: string } }) {
  const companyId = params.id;
  const { data, error, loading, refresh } = useApiData<Opportunity[]>(`/api/companies/${companyId}/opportunities`);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} retry={refresh} />;
  if (!data || data.length === 0) {
    return <EmptyState title="No opportunities detected yet"
      hint="The opportunity engine looks for revenue growth, margin expansion, R&D acceleration, international expansion and balance-sheet strength." />;
  }
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {data.map((o) => <OpportunityCard key={o.id} opportunity={o} companyId={companyId} />)}
    </div>
  );
}
