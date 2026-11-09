import { api } from '../client'
import { isMock } from '../config'
import { EP } from '../endpoints'
import { mock } from '../mock'
import { MOCK_DASHBOARD } from '../mocks/dashboard'

export const dashboardService = {
  /** Everything the dashboard needs in one call: recent activity, real Vault storage, resource links, upcoming court holidays and vacations. */
  get: signal => (isMock('dashboard') ? mock(MOCK_DASHBOARD) : api.get(EP.dashboard, { signal })),
}
