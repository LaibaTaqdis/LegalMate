import { api } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock, uid } from '../mock'
import { CATEGORIES, MOCK_QUESTIONS } from '../mocks/community'
import { MOCK_USER } from '../mocks/user'

const toCard = q => ({ id: q.id, title: q.title, category: q.category, authorName: q.anonymous ? 'Anonymous' : q.authorName, createdAt: q.createdAt, viewCount: q.viewCount, answerCount: q.answers.length, hasExpertAnswer: q.answers.some(a => a.isExpert) })

function mockList({ category, sort = 'trending', q }) {
  let list = MOCK_QUESTIONS.filter(x => {
    if (category && x.category !== category) return false
    if (q && !`${x.title} ${x.body}`.toLowerCase().includes(q.toLowerCase())) return false
    return true
  })
  list = sort === 'recent'
    ? [...list].sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    : [...list].sort((a, b) => (b.viewCount + b.answers.length * 25) - (a.viewCount + a.answers.length * 25))
  return { items: list.map(toCard), total: list.length }
}

export const communityService = {
  /** -> { items: [{ key: category, count }] } */
  categories: signal => (USE_MOCKS ? mock({ items: CATEGORIES.map(c => ({ key: c, count: MOCK_QUESTIONS.filter(q => q.category === c).length })) }) : api.get(EP.community.categories, { signal })),

  /** filters: { category, sort: 'trending'|'recent', q } -> { items, total } */
  list: (filters, signal) => (USE_MOCKS ? mock(mockList(filters)) : api.get(EP.community.questions, { query: filters, signal })),

  /** -> full Question with answers */
  get: (id, signal) => (USE_MOCKS ? mock(MOCK_QUESTIONS.find(q => q.id === id)) : api.get(EP.community.question(id), { signal })),

  /** payload: { title, category, body, privacy: 'public'|'anonymous' } -> Question */
  create: payload => {
    if (!USE_MOCKS) return api.post(EP.community.questions, payload)
    const question = {
      id: uid('q'), title: payload.title, category: payload.category, body: payload.body,
      authorName: MOCK_USER.name, anonymous: payload.privacy === 'anonymous',
      createdAt: new Date().toISOString(), viewCount: 1, answers: [],
    }
    MOCK_QUESTIONS.unshift(question)
    return mock(question, 500)
  },

  /** payload: { text } -> Answer */
  answer: (questionId, payload) => {
    if (!USE_MOCKS) return api.post(EP.community.answers(questionId), payload)
    const question = MOCK_QUESTIONS.find(q => q.id === questionId)
    const answer = { id: uid('a'), authorName: MOCK_USER.name, isExpert: false, text: payload.text, upvotes: 0, createdAt: new Date().toISOString() }
    question.answers.push(answer)
    return mock(answer, 400)
  },
}
