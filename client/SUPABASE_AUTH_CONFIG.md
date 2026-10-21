# 🔐 Supabase Authentication Configuration

This document outlines the required Supabase configuration for authentication redirects in both development and production environments.

## 📋 Redirect URLs Configuration

### In Supabase Dashboard

1. **Go to your Supabase project dashboard**
   - Visit [app.supabase.com](https://app.supabase.com)
   - Select your project: `your-project-ref`

2. **Navigate to Authentication > Settings**
   - In the left sidebar: `Authentication` > `Settings`

3. **Configure Site URL and Redirect URLs**

#### Site URL
```
Production: https://your-production-domain.com
Development: http://localhost:5173
```

#### Additional Redirect URLs
Add these URLs to the "Redirect URLs" section:

**For Development:**
```
http://localhost:5173/reset-password
http://localhost:5173/login
http://localhost:5173/login?confirmed=true
```

**For Production:**
```
https://your-production-domain.com/reset-password
https://your-production-domain.com/login
https://your-production-domain.com/login?confirmed=true
```

## 🚀 Environment-Specific Configuration

### Development (localhost:5173)
- Password reset emails will redirect to: `http://localhost:5173/reset-password`
- Email confirmations will redirect to: `http://localhost:5173/login?confirmed=true`

### Production
- Password reset emails will redirect to: `https://your-domain.com/reset-password`
- Email confirmations will redirect to: `https://your-domain.com/login?confirmed=true`

## ⚙️ Code Implementation

The application automatically detects the environment and uses the appropriate URLs:

```typescript
// In src/lib/auth-config.ts
export const getAuthRedirectUrls = () => {
  const isDev = import.meta.env.DEV
  const baseUrl = isDev 
    ? 'http://localhost:5173'
    : window.location.origin

  return {
    passwordReset: `${baseUrl}/reset-password`,
    emailConfirmation: `${baseUrl}/login?confirmed=true`,
  }
}
```

## 🔧 Routes Available

The application includes these authentication routes:

- `/login` - Sign in page
- `/signup` - User registration page
- `/forgot-password` - Password reset request page
- `/reset-password` - Password reset form (handles magic link)

## 📧 Email Templates (Optional)

You can customize the email templates in Supabase Dashboard:
1. Go to `Authentication` > `Email Templates`
2. Customize the "Reset Password" template
3. Customize the "Confirm Signup" template (if email verification enabled)

## 🛡️ Security Notes

1. **HTTPS in Production**: Always use HTTPS for production redirect URLs
2. **Domain Validation**: Supabase validates redirect URLs against your configured list
3. **Wildcard Domains**: Not recommended for security reasons - specify exact URLs

## 🧪 Testing

### Test Password Reset Flow:
1. Go to `/forgot-password`
2. Enter email address
3. Check email for reset link
4. Click link → should redirect to `/reset-password`
5. Enter new password
6. Should redirect to `/login`

### Test Magic Links (if enabled):
1. Sign up with new email
2. Check email for confirmation link
3. Click link → should redirect to `/login?confirmed=true`

## 📝 Production Deployment Checklist

Before deploying to production:

- [ ] Update Site URL in Supabase Dashboard to production domain
- [ ] Add production redirect URLs to Supabase Dashboard
- [ ] Test password reset flow in production
- [ ] Test email confirmation flow (if enabled)
- [ ] Verify all auth redirects work correctly
- [ ] Check that localhost URLs are removed from production config

## 🐛 Troubleshooting

### "Invalid Redirect URL" Error
- Verify the redirect URL is added to Supabase Dashboard
- Check that the URL exactly matches (including protocol and port)
- Ensure no trailing slashes if not specified in config

### Password Reset Link Not Working
- Check that `/reset-password` route exists in your React app
- Verify the link contains `access_token` and `refresh_token` parameters
- Check browser console for JavaScript errors

### Email Not Sending
- Supabase includes built-in SMTP for development/testing
- For production, configure custom SMTP in Supabase Dashboard
- Check spam folder for reset emails