export type RunData = {
  id: string;
  query: string;
  status: "queued" | "running" | "completed" | "partial" | "failed" | "cancelled";
  stage: string;
  mode: string;
  progress: {
    jobs_collected: number;
    jobs_deduplicated: number;
    jobs_extracted: number;
    jobs_failed: number;
  };
  warnings: string[];
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  report_id: string | null;
};

export type Claim = {
  text?: string;
  rationale?: string;
  evidence_ref: string;
};

export type EvidenceRef = {
  id: string;
  label: string;
  value: number | string;
  metric: string;
  job_ids: string[];
};

export type EvidenceJob = {
  id: string;
  title: string;
  company: string;
  url: string;
  city: string | null;
  family: string;
  posted_at: string | null;
};

export type SkillInsight = {
  skill: string;
  category: string;
  skill_type: string;
  jobs: number;
  pct: number;
  required_jobs: number;
  preferred_jobs: number;
  evidence_ref: string;
};

export type ReportData = {
  id: string;
  run_id: string;
  query: string;
  status: string;
  validation_status: string;
  corpus_job_count: number;
  corpus_company_count: number;
  generated_at: string;
  markdown: string;
  report: {
    title: string;
    query: string;
    generated_at: string;
    corpus: {
      jobs: number;
      companies: number;
      sources: number;
      date_range: { start: string | null; end: string | null };
      salary_coverage: number;
      snapshot: boolean;
    };
    executive_summary: Claim[];
    sections: { heading: string; claims: Claim[] }[];
    recommendations: {
      priority: number;
      skill: string;
      rationale: string;
      effort: string;
      evidence_ref: string;
    }[];
    caveats: string[];
    insights: {
      top_skills: SkillInsight[];
      degrees: { level: string; jobs: number; evidence_ref: string }[];
      certifications: { name: string; jobs: number; evidence_ref: string }[];
      experience: { bucket: string; jobs: number; evidence_ref: string }[];
      companies: { company: string; jobs: number; evidence_ref: string }[];
      languages: { name: string; jobs: number; evidence_ref: string }[];
      cooccurrence: {
        skills: string[];
        matrix: number[][];
        pairs: { a: string; b: string; count: number; jaccard: number }[];
      };
    };
    evidence_refs: EvidenceRef[];
    evidence_jobs: Record<string, EvidenceJob>;
    validation: { status: string; violations?: string[]; checked_claims?: number };
  };
};

export type JobData = {
  id: string;
  title: string;
  company: string;
  location_text: string;
  city: string | null;
  country: string;
  url: string;
  posted_at: string | null;
  collected_at: string;
  job_family: string;
  language: string;
  employment_type: string | null;
  work_mode: string | null;
};

export type JobDetail = JobData & {
  description: string;
  extraction: Record<string, unknown> | null;
};
