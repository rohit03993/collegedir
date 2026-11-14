import type {
  ArticleDetail,
  ArticleList,
  CollegeDetail,
  CollegeList,
  CourseDetail,
  CourseList,
  ExamDetail,
  ExamList,
  HomePayload,
  PredictPayload,
  ScholarshipDetail,
  ScholarshipList,
} from './types';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function apiBase() {
  const configured = import.meta.env.API_URL;
  return configured || 'http://127.0.0.1:8000';
}

export async function fetchJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}${path}`);
  } catch {
    throw new ApiError(503, 'Start the catalogue API at http://127.0.0.1:8000.');
  }
  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      detail = '';
    }
    if (!detail || detail === 'Not Found') {
      detail = 'The catalogue API is not running. From the repo root, start uvicorn api.main:app --port 8000.';
    }
    throw new ApiError(response.status, detail);
  }
  return response.json();
}

export function getHome() {
  return fetchJson<HomePayload>('/api/home');
}

export function getColleges(params: URLSearchParams) {
  const query = params.toString();
  return fetchJson<CollegeList>(`/api/colleges${query ? `?${query}` : ''}`);
}

export function getCollege(slug: string) {
  return fetchJson<CollegeDetail>(`/api/colleges/${encodeURIComponent(slug)}`);
}

export function getExams(params: URLSearchParams) {
  return fetchJson<ExamList>(`/api/exams?${params.toString()}`);
}

export function getExam(slug: string) {
  return fetchJson<ExamDetail>(`/api/exams/${encodeURIComponent(slug)}`);
}

export function getCourses(params: URLSearchParams) {
  return fetchJson<CourseList>(`/api/courses?${params.toString()}`);
}

export function getCourse(slug: string) {
  return fetchJson<CourseDetail>(`/api/courses/${encodeURIComponent(slug)}`);
}

export function getArticles(params: URLSearchParams) {
  return fetchJson<ArticleList>(`/api/articles?${params.toString()}`);
}

export function getArticle(slug: string) {
  return fetchJson<ArticleDetail>(`/api/articles/${encodeURIComponent(slug)}`);
}

export function getScholarships(params: URLSearchParams) {
  return fetchJson<ScholarshipList>(`/api/scholarships?${params.toString()}`);
}

export function getScholarship(slug: string) {
  return fetchJson<ScholarshipDetail>(`/api/scholarships/${encodeURIComponent(slug)}`);
}

export function getPrediction(params: URLSearchParams) {
  const query = params.toString();
  return fetchJson<PredictPayload>(`/api/predict${query ? `?${query}` : ''}`);
}
