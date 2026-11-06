import { api } from '../client'
import { isMock } from '../config'
import { EP } from '../endpoints'
import { mock } from '../mock'

/** Choices offered by the setup form. The backend accepts exactly these values (they are placed in the model's prompt). */
export const PROFILE_OPTIONS = {
  provinces: ['Punjab', 'Sindh', 'Khyber Pakhtunkhwa', 'Balochistan', 'Islamabad Capital Territory', 'Gilgit-Baltistan', 'Azad Jammu & Kashmir'],
  userTypes: ['Citizen', 'Young adult', 'Business owner (SME)', 'Student'],
  employment: ['Employed', 'Self-employed', 'Unemployed', 'Student', 'Retired'],
  roles: ['Tenant', 'Landlord', 'Employee', 'Employer', 'Business owner', 'Property buyer or seller', 'Parent or guardian'],
  ageBands: ['18-24', '25-34', '35-44', '45-59', '60+'],
  marital: ['Single', 'Married', 'Divorced', 'Widowed', 'Prefer not to say'],
  interests: ['Property and tenancy', 'Family', 'Criminal', 'Employment', 'Business and contracts', 'Consumer', 'Cyber and online', 'Constitutional rights'],
}

const EMPTY = { province: null, city: null, userType: null, employmentStatus: null, roles: [], ageBand: null, maritalStatus: null, language: 'en', interests: [], completed: false }
let mockProfile = { ...EMPTY }

export const profileService = {
  /** -> { province, city, userType, employmentStatus, roles[], ageBand, maritalStatus, language, interests[], completed } */
  get: signal => (isMock('profile') ? mock(mockProfile, 150) : api.get(EP.settings.onboardingProfile, { signal })),

  /** Saves the answers (all optional). Only non-identifying facts: they tailor the chatbot's answers. */
  save: profile => {
    if (isMock('profile')) { mockProfile = { ...EMPTY, ...profile, completed: true }; return mock(mockProfile, 300) }
    return api.put(EP.settings.onboardingProfile, profile)
  },
}
