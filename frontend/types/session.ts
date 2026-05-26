export interface JobSummary {
  id: string;
  title: string;
}

export interface SessionSummary {
  session_id: string;
  status: string;
  created_at: string;
  job: JobSummary;
  resume_score: number | null;
}

export interface ResumeReport {
  score: number;
  reference_to_jd: string;
  strengths: string[];
  weaknesses: string[];
}

export interface StartSessionResponse {
  livekit_token: string;
  livekit_url: string;
  room_name: string;
  status: string;
}

export interface DimensionScore {
  score: number;
  max_score: number;
  label: string;
  verdict: string;
  evidence: string;
  strengths: string[];
  gaps: string[];
}

export interface InterviewAssessment {
  overall_score: number;
  practice_verdict: string;
  hire_recommendation?: string;       // Strong Yes | Yes | Maybe | No | Strong No
  summary: string;
  dimension_scores: Record<string, DimensionScore>;
  overall_strengths: string[];
  overall_gaps: string[];
  red_flags?: string[];
  technical_round_probes: string[];
  advance_to_technical?: boolean;
  advance_reasoning?: string;
  candidate_level?: string;           // fresher | junior | mid | senior
  interview_quality?: string;         // complete | partial | incomplete
  turns_analyzed: number;
  completion_ratio: number;
}

export interface MandatorySkillCheck {
  skill: string;
  status: "PRESENT + PROVEN" | "PRESENT + WEAK" | "ABSENT";
  evidence: string;
}

export interface GoodToHaveCheck {
  skill: string;
  present: boolean;
  evidence: string;
}

export interface SectionScores {
  experience?: number;
  core_skills?: number;
  good_to_have?: number;
  consistency?: number;
  education?: number;
  ai_holistic?: number;
}

export interface EnhancedAnalysis {
  // ATS scoring
  ats_score: number | null;
  ats_explanation: string;
  improvements: string[];
  // JD match scoring (from RANKING_PROMPT)
  match_score: number | null;
  gaps: string[];
  strengths: string[];
  summary: string;
  section_scores: SectionScores;
  section_reasons: Record<string, string>;
  mandatory_skills_check: MandatorySkillCheck[];
  good_to_have_check: GoodToHaveCheck[];
  flags: {
    integrity_alert?: boolean;
    fishy_dates_flag?: boolean;
    unexplained_gap_found?: boolean;
    freelance_flag?: boolean;
    jd_title_skill_failed?: boolean;
    date_integrity_violations?: string[];
  };
  dropped?: boolean;
  // Legacy fields (kept for backward compat)
  core_strengths?: string[];
  explanation?: string;
}

export interface TranscriptTurn {
  speaker: "agent" | "candidate";
  text: string;
  created_at?: number;
}

export interface SessionDetail {
  session_id: string;
  status: string;
  created_at: string;
  job: JobSummary;
  resume_report: ResumeReport | null;
  resume_score: number | null;
  interview_assessment: InterviewAssessment | null;
  enhanced_analysis: EnhancedAnalysis | null;
  transcript: TranscriptTurn[] | null;
}
