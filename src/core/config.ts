import { z } from "zod";

const envSchema = z.object({
  NODE_ENV: z.string().default("development"),

  APP_NAME: z.string().default("ShortZlinks"),
  APP_URL: z.string(),
  APP_TIMEZONE: z.string().default("Asia/Kolkata"),
  APP_LOCALE: z.string().default("en"),

  MONGODB_URI: z.string(),
  MONGODB_DB_NAME: z.string(),

  REDIS_URL: z.string().optional(),

  JWT_ACCESS_SECRET: z.string(),
  JWT_REFRESH_SECRET: z.string(),
  SESSION_SECRET: z.string(),
  SESSION_MAX_AGE_HOURS: z.coerce.number(),

  SMTP_HOST: z.string().optional(),
  SMTP_PORT: z.coerce.number().optional(),
  SMTP_USER: z.string().optional(),
  SMTP_PASS: z.string().optional(),
  SMTP_FROM_EMAIL: z.string().optional(),
  SMTP_FROM_NAME: z.string().optional(),

  BREVO_API_KEY: z.string().optional(),

  BOT_ENABLED: z.string().default("false"),
  TELEGRAM_BOT_TOKEN: z.string().optional(),
  TELEGRAM_BOT_USERNAME: z.string().optional(),

  API_KEY_PREFIX: z.string().default("sk_live_"),
  API_RATE_LIMIT_PER_MIN: z.coerce.number().default(60),

  MIN_WITHDRAW_AMOUNT: z.coerce.number().default(200),
  WITHDRAW_OPEN_DAY: z.coerce.number().default(24),
  WITHDRAW_CLOSE_DAY: z.coerce.number().default(30),

  PROXY_CHECK_ENABLED: z.string().default("true"),
  CLICK_LIMIT_HOURS: z.coerce.number().default(24),
  CLICK_LIMIT_PER_IP: z.coerce.number().default(1),

  TURNSTILE_SITE_KEY: z.string().optional(),
  TURNSTILE_SECRET_KEY: z.string().optional(),

  RECAPTCHA_SITE_KEY: z.string().optional(),
  RECAPTCHA_SECRET_KEY: z.string().optional(),

  HCAPTCHA_SITE_KEY: z.string().optional(),
  HCAPTCHA_SECRET_KEY: z.string().optional(),

  DEFAULT_ROUTE_STEPS: z.coerce.number().default(2),
  DEFAULT_STEP1_TIMER: z.coerce.number().default(15),
  DEFAULT_STEP2_TIMER: z.coerce.number().default(10),
  DEFAULT_STEP3_TIMER: z.coerce.number().default(10),

  ADBLOCK_PROTECTION: z.string().default("true"),

  PRIMARY_SHORT_DOMAIN: z.string().optional(),
  FALLBACK_SHORT_DOMAINS: z.string().optional(),

  STORAGE_DRIVER: z.string().default("local"),
  S3_ENDPOINT: z.string().optional(),
  S3_REGION: z.string().optional(),
  S3_BUCKET: z.string().optional(),
  S3_ACCESS_KEY: z.string().optional(),
  S3_SECRET_KEY: z.string().optional()
});

export const env = envSchema.parse(process.env);

export default env;
