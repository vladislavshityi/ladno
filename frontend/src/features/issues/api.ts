import { api } from '@/lib/api-client'
import type {
  Category,
  Classification,
  Issue,
  IssueCreate,
  IssuePatch,
  Photo,
  Question,
  RouteRequest,
  RouteResult,
  SendChannel,
  SendResponse,
  Submission,
} from '@/types/models'

export const issuesApi = {
  categories: () => api.get<Category[]>('/categories'),
  questions: (category: string) => api.get<Question[]>(`/categories/${category}/questions`),
  uploadPhoto: (file: File) => api.upload<Photo>('/photos', file),
  classify: (body: { text: string; photo_ids: string[] }) => api.post<Classification>('/issues/classify', body),
  route: (body: RouteRequest) => api.post<RouteResult>('/issues/route', body),
  create: (body: IssueCreate) => api.post<Issue>('/issues', body),
  list: () => api.get<Issue[]>('/issues'),
  get: (id: string) => api.get<Issue>(`/issues/${id}`),
  patch: (id: string, body: IssuePatch) => api.patch<Issue>(`/issues/${id}`, body),
  submission: (id: string) => api.get<Submission>(`/issues/${id}/submission`),
  channels: (id: string) => api.get<SendChannel[]>(`/issues/${id}/channels`),
  send: (id: string, channel: SendChannel['name']) => api.post<SendResponse>(`/issues/${id}/send`, { channel }),
  /** The letter PDF is private too, so it is fetched with the token. */
  letterPdf: async (id: string) => (await api.raw('GET', `/issues/${id}/letter.pdf`)).blob(),
  refreshLetter: (id: string) => api.post<Issue>(`/issues/${id}/refresh-letter`),
  escalate: (id: string) => api.post<Issue>(`/issues/${id}/escalate`),
  /** Photos are private: the file is fetched with the token and turned into an object URL. */
  photoBlob: async (url: string) => (await api.raw('GET', url.replace(/^\/api/, ''))).blob(),
}
