import bcrypt from 'bcryptjs';
import { SignJWT, jwtVerify, JWTPayload } from 'jose';
import { cookies } from 'next/headers';
import crypto from 'crypto';
import { connectDB } from './db';
import { User } from './models';
import config from './config';

// -----------------------------------------------------------------------------
// Types & Interfaces
// -----------------------------------------------------------------------------

export interface AuthJwtPayload extends JWTPayload {
  userId: string;
  role: string;
}

export interface SessionResult {
  accessToken: string;
  refreshToken: string;
}

// Ensure secrets are properly encoded for 'jose'
const getAccessSecret = () => new TextEncoder().encode(config.JWT_SECRET);
const getRefreshSecret = () => new TextEncoder().encode(config.JWT_REFRESH_SECRET);

// -----------------------------------------------------------------------------
// Password Hashing
// -----------------------------------------------------------------------------

/**
 * Hashes a plaintext password using bcryptjs.
 */
export async function hashPassword(password: string): Promise<string> {
  const saltRounds = 12;
  return await bcrypt.hash(password, saltRounds);
}

/**
 * Verifies a plaintext password against a stored hash.
 */
export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return await bcrypt.compare(password, hash);
}

// -----------------------------------------------------------------------------
// JWT Generation & Verification
// -----------------------------------------------------------------------------

/**
 * Generates a short-lived access token.
 */
export async function generateAccessToken(payload: AuthJwtPayload): Promise<string> {
  return new SignJWT(payload)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('15m') // Access tokens should be short-lived
    .sign(getAccessSecret());
}

/**
 * Generates a long-lived refresh token.
 */
export async function generateRefreshToken(payload: AuthJwtPayload): Promise<string> {
  const expiresInHours = config.SESSION_MAX_AGE_HOURS || 24 * 7; // Default to 7 days if undefined
  return new SignJWT(payload)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(`${expiresInHours}h`)
    .sign(getRefreshSecret());
}

/**
 * Verifies an access token and extracts its payload.
 */
export async function verifyAccessToken(token: string): Promise<AuthJwtPayload> {
  try {
    const { payload } = await jwtVerify(token, getAccessSecret());
    return payload as AuthJwtPayload;
  } catch (error) {
    throw new Error('Invalid or expired access token');
  }
}

/**
 * Verifies a refresh token and extracts its payload.
 */
export async function verifyRefreshToken(token: string): Promise<AuthJwtPayload> {
  try {
    const { payload } = await jwtVerify(token, getRefreshSecret());
    return payload as AuthJwtPayload;
  } catch (error) {
    throw new Error('Invalid or expired refresh token');
  }
}

// -----------------------------------------------------------------------------
// Session Management
// -----------------------------------------------------------------------------

/**
 * Creates a new session by generating tokens and setting HTTP-only cookies.
 */
export async function createSession(userId: string, role: string): Promise<SessionResult> {
  const payload: AuthJwtPayload = { userId, role };
  
  const accessToken = await generateAccessToken(payload);
  const refreshToken = await generateRefreshToken(payload);

  const cookieStore = cookies();
  const maxAgeSeconds = (config.SESSION_MAX_AGE_HOURS || 168) * 3600;

  cookieStore.set('accessToken', accessToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 15 * 60, // 15 minutes
  });

  cookieStore.set('refreshToken', refreshToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: maxAgeSeconds,
  });

  return { accessToken, refreshToken };
}

/**
 * Destroys the current session by clearing authentication cookies.
 */
export async function destroySession(): Promise<void> {
  const cookieStore = cookies();
  cookieStore.delete('accessToken');
  cookieStore.delete('refreshToken');
}

// -----------------------------------------------------------------------------
// Route Guards & User Retrieval
// -----------------------------------------------------------------------------

/**
 * Retrieves the currently authenticated user from the database based on cookies.
 * Attempts to use the access token first, then falls back to the refresh token.
 */
export async function getCurrentUser() {
  const cookieStore = cookies();
  const accessToken = cookieStore.get('accessToken')?.value;
  const refreshToken = cookieStore.get('refreshToken')?.value;

  let userId: string | null = null;

  if (accessToken) {
    try {
      const payload = await verifyAccessToken(accessToken);
      userId = payload.userId;
    } catch (error) {
      // Access token invalid/expired, will try refresh token below
    }
  }

  if (!userId && refreshToken) {
    try {
      const payload = await verifyRefreshToken(refreshToken);
      userId = payload.userId;
      
      // Optionally: Rotate access token here by calling createSession or just setting a new access cookie
      const newAccessToken = await generateAccessToken({ userId, role: payload.role });
      cookieStore.set('accessToken', newAccessToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/',
        maxAge: 15 * 60,
      });
    } catch (error) {
      return null; // Both tokens invalid
    }
  }

  if (!userId) return null;

  await connectDB();
  const user = await User.findById(userId).select('-password').lean().exec();
  
  return user ? Object.assign(user, { _id: user._id.toString() }) : null;
}

/**
 * Requires a valid authenticated user. Throws an error if unauthorized.
 */
export async function requireUser() {
  const user = await getCurrentUser();
  if (!user) {
    throw new Error('UNAUTHORIZED');
  }
  // Check if account is suspended or banned
  if (user.status !== 'active') {
    throw new Error('ACCOUNT_DISABLED');
  }
  return user;
}

/**
 * Requires a valid authenticated admin. Throws an error if unauthorized.
 */
export async function requireAdmin() {
  const user = await requireUser();
  if (user.role !== 'admin') {
    throw new Error('FORBIDDEN');
  }
  return user;
}

/**
 * Requires a valid authenticated staff member or admin. Throws an error if unauthorized.
 */
export async function requireStaff() {
  const user = await requireUser();
  if (user.role !== 'admin' && user.role !== 'staff') {
    throw new Error('FORBIDDEN');
  }
  return user;
}

// -----------------------------------------------------------------------------
// Utility Functions
// -----------------------------------------------------------------------------

/**
 * Generates a cryptographically secure, URL-safe API key.
 * Format: sz_{randomHex}
 */
export function generateApiKey(): string {
  const prefix = 'sz_';
  const randomBytes = crypto.randomBytes(32).toString('hex');
  return `${prefix}${randomBytes}`;
}
