import { api } from '../client'
import { USE_MOCKS } from '../config'
import { EP } from '../endpoints'
import { mock, uid } from '../mock'
import { MOCK_EMERGENCY_CATEGORIES, MOCK_HELPLINE, MOCK_PERSONAL_CONTACTS } from '../mocks/emergency'

// Mutated in place in mock mode so added/removed contacts persist across the session.
const contacts = [...MOCK_PERSONAL_CONTACTS]

export const emergencyService = {
  /** -> { helpline, categories: [{ key, label, icon, numbers: [{ label, number }] }] } */
  contacts: signal =>
    USE_MOCKS ? mock({ helpline: MOCK_HELPLINE, categories: MOCK_EMERGENCY_CATEGORIES }) : api.get(EP.emergency.categories, { signal }),

  /** -> { items: PersonalContact[] } */
  myContacts: signal => (USE_MOCKS ? mock({ items: contacts }) : api.get(EP.emergency.personalContacts, { signal })),

  /** payload: { name, relation, phone } -> PersonalContact */
  addContact: payload => {
    if (!USE_MOCKS) return api.post(EP.emergency.personalContacts, payload)
    const contact = { id: uid('ec'), primary: false, ...payload }
    contacts.push(contact)
    return mock(contact, 300)
  },

  removeContact: id => {
    if (!USE_MOCKS) return api.delete(EP.emergency.personalContact(id))
    const i = contacts.findIndex(c => c.id === id)
    if (i >= 0) contacts.splice(i, 1)
    return mock(null, 150)
  },

  /** payload: { contactId, shareLocation } -> { sentAt, notifiedContact } */
  sendAlert: payload => {
    if (!USE_MOCKS) return api.post(EP.emergency.alert, payload)
    const notifiedContact = contacts.find(c => c.id === payload.contactId) || contacts.find(c => c.primary) || contacts[0]
    return mock({ sentAt: new Date().toISOString(), notifiedContact }, 900)
  },
}
