export interface UserOut {
  id: string
  email: string
  full_name: string
  phone_number: string | null
  phone_verified: boolean
  sms_notifications: boolean
}
