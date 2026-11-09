export type Subject = { id: number; name: string; slug: string; icon: string; color: string; description?: string };
export type Examination = {
  id: number; name: string; code: string; full_name: string; description: string; color: string;
  min_subjects: number; max_subjects: number; rules_note: string; mock_duration_minutes: number;
  subjects: { subject: Subject; is_compulsory: boolean }[];
};
export type StudentExam = {
  id: number; examination: Examination; exam_date: string | null; subjects: Subject[]; daily_minutes: number;
  study_days: number[]; target_score: number | null; onboarding_step: string; days_left: number | null; created_at: string;
};
export type Profile = {
  display_name: string; avatar_color: string; state: string; school: string; study_goal: string;
  daily_goal_minutes: number; leaderboard_visibility: "public" | "anonymous" | "hidden";
  notify_email_reminders: boolean; notify_streak: boolean; notify_product: boolean; total_xp: number; level: number;
  onboarding_completed: boolean; active_student_exam: number | null;
};
export type Me = {
  id: number; email: string; full_name: string; role: "student" | "content_manager" | "admin"; referral_code: string;
  date_joined: string; profile: Profile; balance: number; student_exams: StudentExam[];
};
export type Option = { id: number; label: string; text: string };
export type QuizQuestion = {
  id: number; order: number; text: string; image_url: string | null; table: any; difficulty: string; topic: string | null;
  subject: string; exam_year: number | null; is_official_past_question: boolean;
  passage: { title: string; body: string } | null; options: Option[]; selected_option: number | null; flagged: boolean;
  answered: boolean; is_correct?: boolean | null; correct_option?: number | null; explanation?: string; solution_steps?: string[];
};
export type Attempt = {
  id: number; kind: string; kind_label: string; mode: "practice" | "exam"; status: string; subject: number | null;
  subject_name: string | null; topic: number | null; topic_name: string | null; hearts_enabled: boolean;
  hearts_remaining: number; time_limit_seconds: number | null; started_at: string; submitted_at: string | null;
  deadline: string | null; total_questions: number; correct_count: number; score_percent: string | null;
  time_spent_seconds: number; xp_earned: number; credits_charged: number; result_summary: any; questions: QuizQuestion[];
};
export type Pricing = { key: string; label: string; credits: number };
