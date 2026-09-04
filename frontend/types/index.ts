// API response types (mirror backend Pydantic schemas)
export interface Company {
  id: string;
  name: string;
  ticker: string;
  industry: string;
  country: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface CompanySummary extends Company {
  document_count: number;
  risk_level: string;
  risk_score: number;
  financial_health: number | null;
  growth_potential: number | null;
  last_analyzed_at: string | null;
}

export interface ScoreCard {
  label: string;
  score: number;
  level: string;
  detail: string;
}

export interface CompanyOverview {
  company: Company;
  scorecards: ScoreCard[];
  document_count: number;
  ready_document_count: number;
  last_analyzed_at: string | null;
  top_risks: RiskSummaryItem[];
  top_opportunities: OpportunitySummaryItem[];
  recent_documents: DocumentItem[];
  revenue_trend: { period: string; total_revenue?: number | null; ebitda?: number | null; net_income?: number | null }[];
  report_id: string | null;
}

export interface RiskSummaryItem {
  id: string;
  title: string;
  category: string;
  severity: string;
  score: number;
  explanation: string;
}

export interface OpportunitySummaryItem {
  id: string;
  title: string;
  category: string;
  confidence: string;
  description: string;
}

export interface DocumentItem {
  id: string;
  company_id: string;
  filename: string;
  document_type: string;
  fiscal_year: number | null;
  source_url: string;
  file_hash: string;
  page_count: number;
  status: string;
  error_message: string;
  file_size: number;
  created_at: string;
  processed_at: string | null;
}

export interface DocumentPage {
  document_id: string;
  page_number: number;
  text: string;
  meta: Record<string, unknown>;
}

export interface Citation {
  source_id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  section: string;
  quote: string;
  relevance: number;
}

export interface Claim {
  text: string;
  type: string;
  sources: string[];
}

export interface ChatAnswer {
  answer: string;
  confidence: string;
  claims: Claim[];
  citations: Citation[];
  insufficient_evidence: boolean;
  session_id: string;
  message_id: string;
  provider: string;
}

export interface ChatMessageItem {
  id: string;
  role: string;
  content: string;
  meta: { confidence?: string; claims?: Claim[]; insufficient_evidence?: boolean; provider?: string };
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  messages: ChatMessageItem[];
}

export interface RiskEvidenceItem {
  id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  section: string;
  quote: string;
}

export interface Risk {
  id: string;
  company_id: string;
  category: string;
  title: string;
  severity: string;
  score: number;
  explanation: string;
  why_it_matters: string;
  potential_impact: string;
  recommendation: string;
  confidence: string;
  detected_signals: Record<string, unknown>;
  evidence: RiskEvidenceItem[];
  created_at: string;
}

export interface Opportunity {
  id: string;
  company_id: string;
  category: string;
  title: string;
  description: string;
  potential_impact: string;
  confidence: string;
  evidence: RiskEvidenceItem[];
  created_at: string;
}

export interface Inconsistency {
  id: string;
  topic: string;
  claim_a: string;
  claim_b: string;
  source_a_document_id: string | null;
  source_a_page: number;
  source_b_document_id: string | null;
  source_b_page: number;
  explanation: string;
  severity: string;
  created_at: string;
}

export interface ManagementQuestion {
  id: string;
  topic: string;
  question: string;
  rationale: string;
  priority: string;
}

export interface MetricItem {
  metric: string;
  value: number;
  currency: string;
  unit: string;
  period_label: string;
  source_document_id: string | null;
  source_page: number;
  confidence: number;
}

export interface FinancialPeriodItem {
  period_label: string;
  fiscal_year: number;
  currency: string;
  unit: string;
  metrics: MetricItem[];
  ratios: Record<string, number | null>;
}

export interface TrendPoint {
  period_label: string;
  values: Record<string, number | null>;
}

export interface Financials {
  periods: FinancialPeriodItem[];
  trends: TrendPoint[];
  summary: { growth: Record<string, number | null>; cagrs: Record<string, number | null> };
}

export interface ChangeItem {
  label: string;
  metric: string;
  from_value: number | null;
  to_value: number | null;
  delta_pct: number | null;
  delta_pts: number | null;
  direction: string;
  sentiment: string;
}

export interface Changes {
  from_period: string;
  to_period: string;
  items: ChangeItem[];
  narrative: string;
}

export interface ReportSummary {
  id: string;
  company_id: string;
  title: string;
  status: string;
  period_from: string | null;
  period_to: string | null;
  overall_risk_score: number;
  created_at: string;
}

export interface ReportContent {
  title: string;
  company: { name: string; ticker: string; industry: string; country: string };
  generated_at: string;
  documents_analyzed: { id: string; filename: string; type: string; fiscal_year: number | null }[];
  scores: { overall_risk: number; financial_health: [number, string]; growth_potential: [number, string] };
  narrative: Record<string, string>;
  financial_table: Record<string, number | string | null>[];
  risks: {
    category: string; title: string; severity: string; score: number;
    explanation: string; why_it_matters: string; potential_impact: string;
    recommendation: string;
    evidence: { document_id: string; document_name: string; page_number: number; quote: string }[];
  }[];
  opportunities: { category: string; title: string; description: string; potential_impact: string; confidence: string }[];
  inconsistencies: Inconsistency[];
  questions: ManagementQuestion[];
  disclaimer: string;
}

export interface ReportDetail extends ReportSummary {
  content: ReportContent;
}

export interface SearchHit {
  document_id: string;
  document_name: string;
  document_type: string;
  fiscal_year: number | null;
  page_number: number;
  section: string;
  excerpt: string;
  score: number;
}

export interface SearchOut {
  query: string;
  total: number;
  hits: SearchHit[];
}

export interface Job {
  id: string;
  kind: string;
  status: string;
  steps: string[];
  current_step: string;
  progress: number;
  result: unknown;
  error: string | null;
  created_at: string;
}

export interface DashboardData {
  companies: {
    id: string; name: string; ticker: string; industry: string;
    document_count: number; risk_level: string;
    financial_health: number | null; growth_potential: number | null;
    last_analyzed_at: string | null;
  }[];
  totals: Record<string, number>;
  recent_activity: { kind: string; company_id: string; company_name: string; label: string; at: string }[];
}
