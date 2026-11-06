import { api } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock } from '../mock'
import { MOCK_DASHBOARD } from '../mocks/dashboard'

export const dashboardService = {
  /** Everything the dashboard needs in one call: activity, vault usage, resources, deadlines, WhatsApp status. */
  get: signal => (USE_MOCKS ? mock(MOCK_DASHBOARD) : api.get(EP.dashboard, { signal })),
}
