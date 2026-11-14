export interface CollegeCardData {
  slug: string;
  name: string;
  city?: string | null;
  state?: string | null;
  ownership?: string | null;
  courseGroup?: string | null;
  fee?: string | null;
  rating?: number | null;
  image?: string | null;
  openingRank?: string | null;
  closingRank?: string | null;
  chance?: string | null;
}

export interface FacetValue {
  value: string;
  count: number;
}

export interface Facets {
  state: FacetValue[];
  city: FacetValue[];
  course: FacetValue[];
  branch: FacetValue[];
  stream: FacetValue[];
}

export interface CollegeList {
  total: number;
  query: string;
  colleges: CollegeCardData[];
  facets: Facets;
}

export interface FeeRow {
  courseName: string | null;
  courseGroup: string | null;
  specialization: string | null;
  duration: string | null;
  year: string | null;
  fee: string | null;
}

export interface FactTable {
  heading: string | null;
  columns: string[];
  rows: string[][];
}

export interface EngineeringFacts {
  nirfRank: number | null;
  feeRange: string | null;
  averagePackage: string | null;
  approval: string | null;
  exams: string | null;
  courses: FactTable[];
  admission: FactTable[];
  placement: FactTable[];
  cutoff: FactTable[];
  scholarship: FactTable[];
}

export interface CollegeDetail {
  slug: string;
  name: string;
  city: string | null;
  state: string | null;
  ownership: string | null;
  established: number | null;
  category: string | null;
  tags: string[];
  approvals: string[];
  rating: number | null;
  reviews: number | null;
  image: string | null;
  logo: string | null;
  gallery: string[];
  overviewHtml: string | null;
  feesText: string | null;
  fees: FeeRow[];
  admissionHtml: string | null;
  cutoffHtml: string | null;
  placementHtml: string | null;
  facilitiesHtml: string | null;
  hostelHtml: string | null;
  faqs: { question: string; answer: string }[];
  facts: EngineeringFacts;
}

export interface HomePayload {
  suggestions: { label: string; href: string }[];
  streams: { name: string; count: number; href: string }[];
  next: { name: string; count: number; href: string }[];
  colleges: CollegeCardData[];
  exams: { name: string; category: string | null; date: string | null; href: string }[];
}

export interface CategoryCount {
  name: string;
  count: number;
}

export interface ExamCard {
  slug: string;
  name: string;
  fullName: string | null;
  category: string | null;
  level: string | null;
  date: string | null;
}

export interface ExamList {
  total: number;
  query: string;
  category: string | null;
  categories: CategoryCount[];
  items: ExamCard[];
}

export interface ExamDetail extends ExamCard {
  mode: string | null;
  eligibility: string | null;
  officialWebsite: string | null;
  summaryHtml: string | null;
  descriptionHtml: string | null;
  patternHtml: string | null;
  applicationHtml: string | null;
  datesHtml: string | null;
  resultHtml: string | null;
  faqs: { question: string; answer: string }[];
}

export interface CourseCard {
  slug: string;
  name: string;
  category: string | null;
  level: string | null;
  duration: string | null;
  mode: string | null;
}

export interface CourseList {
  total: number;
  query: string;
  category: string | null;
  categories: CategoryCount[];
  items: CourseCard[];
}

export interface CourseDetail extends CourseCard {
  eligibility: string | null;
  summary: string | null;
  descriptionHtml: string | null;
  aboutHtml: string | null;
  admissionHtml: string | null;
  subjectsHtml: string | null;
  scopeHtml: string | null;
  faqs: { question: string; answer: string }[];
}

export interface ArticleCard {
  slug: string;
  title: string;
  description: string | null;
  category: string | null;
  author: string | null;
}

export interface ArticleList {
  total: number;
  query: string;
  items: ArticleCard[];
}

export interface ArticleDetail extends ArticleCard {
  contentHtml: string | null;
}

export interface ScholarshipCard {
  slug: string;
  title: string;
  provider: string | null;
  amount: string | null;
  deadline: string | null;
  category: string | null;
  level: string | null;
}

export interface ScholarshipList {
  total: number;
  query: string;
  items: ScholarshipCard[];
}

export interface PredictChoice {
  value: string;
  label: string;
}

export interface PredictOptions {
  exams: string[];
  categories: PredictChoice[];
  genders: PredictChoice[];
  states: string[];
}

export interface PredictFamily {
  name: string;
  count: number;
}

export interface PredictRow {
  college: string;
  slug: string | null;
  state: string;
  branch: string;
  family: string;
  quota: string;
  gender: string;
  openingRank: number | null;
  closingRank: number;
  round: string;
  roundName: string;
  chance: string;
  nirf: number | null;
  fee: string | null;
}

export interface PredictSection {
  id: string;
  title: string;
  detail: string;
  inside: number;
  josaaInside: number;
  csabInside: number | null;
  total: number;
  pageSize?: number;
  families: PredictFamily[];
  rows: PredictRow[];
}

export interface PredictResult {
  exam: string;
  rank: number;
  crl: number | null;
  category: string;
  gender: string;
  homeState: string;
  branch: string;
  note: string;
  sections: PredictSection[];
}

export interface PredictPayload {
  options: PredictOptions;
  result: PredictResult | null;
  error?: string;
}

export interface ScholarshipDetail extends ScholarshipCard {
  eligibilityHtml: string | null;
  descriptionHtml: string | null;
  applyUrl: string | null;
}
