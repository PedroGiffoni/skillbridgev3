import { request } from './account-api'

export type CourseItem = { id: string; title: string; revision: number; plan_id: string; created_at: string }
type CoursePage = { items: CourseItem[]; next_offset: number | null }
export type CourseDraft = Omit<CourseItem, 'title'> & { content: { title: string } }
export type LibraryModule = { id: string; title: string; status: 'locked' | 'open' | 'mastered'; blocked_by: string[] }
export type LessonSlot = {
  outline_id: string; module_id?: string; module_title: string; title: string; objective: string; week: number
  locked?: boolean
  job_id: string | null; lesson_id: string | null; practice_completed: boolean
}
type PracticeItem = { id: string; label: string }
export type PracticeAttempt = { id: string; created_at: string; correct: boolean; hint_used: boolean; feedback: string[] }
export type PracticeProgress = { attempts: number; completed: boolean; latest_attempt: PracticeAttempt | null }
type LessonOverview = {
  id: string; title: string; week: number; objective: string; explanation: string; example: string; summary: string
  practice: PracticeProgress
}
export type Lesson = LessonOverview & (
  | { format: 'multiple_choice'; exercise: { prompt: string; options: PracticeItem[] } }
  | { format: 'order_steps'; exercise: { prompt: string; steps: PracticeItem[] } }
  | { format: 'fill_blank'; exercise: { prompt: string } }
)
export type PracticeAnswer =
  | { kind: 'multiple_choice'; option_id: string }
  | { kind: 'order_steps'; step_ids: string[] }
  | { kind: 'fill_blank'; text: string }
export type CourseJob = {
  id: string
  status: 'queued' | 'running' | 'ready' | 'failed' | 'needs_review'
  attempts: number
  retry_after_seconds: number
  error: { detail: string; retryable: boolean } | null
  draft: CourseDraft | null
  lesson: Lesson | null
}

const courses = '/api/courses'
const coursePath = (id: string) => courses + '/' + encodeURIComponent(id)
export const listCourses = (offset: number, signal: AbortSignal) =>
  request<CoursePage>(courses + '?offset=' + offset, 'GET', undefined, signal)
export const getCourseJob = (planId: string, signal: AbortSignal) =>
  request<{ job: CourseJob | null }>('/api/study-plans/' + encodeURIComponent(planId) + '/course-job', 'GET', undefined, signal)
export const getJob = (jobId: string, signal: AbortSignal) =>
  request<CourseJob>(courses + '/jobs/' + encodeURIComponent(jobId), 'GET', undefined, signal)
export const createCourse = (planId: string, retryAttempt: number | undefined, signal: AbortSignal) =>
  request<CourseJob>(courses + '/generate', 'POST', { plan_id: planId, consent: true, retry_attempt: retryAttempt }, signal)
export const publishCourse = (draft: CourseDraft, signal: AbortSignal) =>
  request<CourseDraft>(coursePath(draft.id) + '/publish', 'POST', { draft_revision: draft.revision }, signal)
export const listLessons = (course: CourseItem, signal: AbortSignal) =>
  request<{ items: LessonSlot[]; modules: LibraryModule[] }>(coursePath(course.id) + '/lessons?course_revision=' + course.revision, 'GET', undefined, signal)
export const prepareLesson = (course: CourseItem, outlineId: string, retryAttempt: number | undefined, signal: AbortSignal) =>
  request<CourseJob>(coursePath(course.id) + '/lessons/' + encodeURIComponent(outlineId) + '/generate', 'POST',
    { course_revision: course.revision, consent: true, retry_attempt: retryAttempt }, signal)
export const getLesson = (lessonId: string, signal: AbortSignal) =>
  request<Lesson>('/api/lessons/' + encodeURIComponent(lessonId), 'GET', undefined, signal)

const exercisePath = (id: string) => '/api/exercises/' + encodeURIComponent(id)
export const requestPracticeHint = (lessonId: string, attemptId: string, signal: AbortSignal) =>
  request<{ text: string; receipt: string }>(exercisePath(lessonId) + '/hint', 'POST', { attempt_id: attemptId }, signal)
export const submitPractice = (lessonId: string, attemptId: string, answer: PracticeAnswer, hintReceipt: string | undefined, signal: AbortSignal) =>
  request<{ attempt: PracticeAttempt; practice: PracticeProgress }>(exercisePath(lessonId) + '/attempts',
    'POST', { attempt_id: attemptId, answer, hint_receipt: hintReceipt }, signal)
