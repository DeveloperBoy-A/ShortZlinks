import { NextRequest, NextResponse } from "next/server";

const USER_ROUTES = [
  "/dashboard",
  "/announcements",
  "/links",
  "/payment",
  "/referrals",
  "/support",
  "/security",
  "/settings",
  "/api",
  "/tools"
];

const ADMIN_ROUTES = ["/admin"];

function isProtectedUserRoute(pathname: string) {
  return USER_ROUTES.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

function isAdminRoute(pathname: string) {
  return ADMIN_ROUTES.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.startsWith("/api/public") ||
    pathname.startsWith("/r/")
  ) {
    return NextResponse.next();
  }

  const accessToken = req.cookies.get("sz_access")?.value;
  const role = req.cookies.get("sz_role")?.value;

  if (isProtectedUserRoute(pathname) && !accessToken) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  if (isAdminRoute(pathname)) {
    if (!accessToken) {
      return NextResponse.redirect(new URL("/login", req.url));
    }
    if (role !== "admin" && role !== "staff") {
      return NextResponse.redirect(new URL("/dashboard", req.url));
    }
  }

  if (accessToken && ["/login", "/register"].includes(pathname)) {
    return NextResponse.redirect(new URL("/dashboard", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!.*\\..*|_next).*)"]
};