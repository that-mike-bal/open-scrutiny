/**
 * Authentication configuration and redirect URLs
 */

export const getAuthRedirectUrls = () => {
  // Use environment variable if available, otherwise fall back to window.location.origin
  const baseUrl = import.meta.env.VITE_FRONTEND_URL || window.location.origin
  
  return {
    // URL to redirect to after password reset email is clicked
    passwordReset: `${baseUrl}/reset-password`,
    
    // URL to redirect to after email confirmation
    emailConfirmation: `${baseUrl}/login?confirmed=true`,
    
    // URL to redirect to after successful login
    defaultRedirect: '/',
    
    // URL to redirect to after logout
    logout: '/login'
  }
}

/**
 * Get the appropriate redirect URL based on the auth event
 */
export const getRedirectUrl = (event: 'password_reset' | 'email_confirmation' | 'login' | 'logout') => {
  const urls = getAuthRedirectUrls()
  
  switch (event) {
    case 'password_reset':
      return urls.passwordReset
    case 'email_confirmation':
      return urls.emailConfirmation
    case 'login':
      return urls.defaultRedirect
    case 'logout':
      return urls.logout
    default:
      return urls.defaultRedirect
  }
}